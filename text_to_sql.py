import os
from dotenv import load_dotenv
import mysql.connector
import google.generativeai as genai
from sentence_transformers import SentenceTransformer
import chromadb
import ast

# load the environment variables
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

#Connect to MySQL
db=mysql.connector.connect(
    host="localhost",
    user="root",
    password="1234",
    database="recipes_db"
)
cursor=db.cursor()

#setup chromaDB
client=chromadb.PersistentClient(path="./chroma_db")
collection=client.get_or_create_collection("sql_schema")

#load embedding model
embedder=SentenceTransformer("all-MiniLM-L6-v2")

#add schema and examples to chroma
schema_docs = [
    "recipes table has columns recipe_id, recipe_title, category, subcategory, description, ingredients, directions, num_ingredients, num_steps.",
    "Query to list all recipes in Dessert category: SELECT recipe_title FROM recipes WHERE category='Dessert';",
    "Query to show total recipes count: SELECT COUNT(*) FROM recipes;",
    "Query to get ingredients for a recipe: SELECT ingredients FROM recipes WHERE recipe_title='Carrot Cake';",
]
if len(collection.get()['ids'])==0:
    print("Adding schema info to chroma...")
    embeddings=embedder.encode(schema_docs)
    for i, doc in enumerate(schema_docs):
        collection.add(ids=[f"doc_{i}"], documents=[doc], embeddings=[embeddings[i]])

#Retrieve context
def retrieve_context(user_query):
    query_emb=embedder.encode([user_query])
    results=collection.query(query_embeddings=query_emb, n_results=2)
    return " ".join(results["documents"][0])

#Generating sql
def generate_sql(user_query):
    context=retrieve_context(user_query)
    prompt = f"""
    You are an expert SQL generator.
    Use this database context to create a valid MySQL query.

    Context:
    {context}

    User question:
    {user_query}

    Output only the SQL query without explanation or formatting.
    """
    response=genai.GenerativeModel("gemini-2.0-flash").generate_content(prompt)
    sql_query=response.text.strip().replace("```sql","").replace("```","")
    return sql_query

def execute_sql(sql_query):
    try:
        cursor.execute(sql_query)
        results=cursor.fetchall()
        return results
    except Exception as e:
        return f"Error executing SQL: {e}"
    
def format_recipe_results(results,user_query):
    output_text=""

    if not results or isinstance(results,str):
        prompt=f"""
        You are professional chef and recipe creator.
        The user asked: "{user_query}" but no recipe was found in the database.
        
        Generate a similar or alternative recipe that matches the user's request.
        Format:
        - Recipe title
        - Short description
        - Ingredients (as bullet points)
        - steps (As numbered instructions)
        """
        response=genai.GenerativeModel("gemini-2.0-flash").generate_content(prompt)
        ai_recipe=response.text.strip()
        output_text+=f"No matching recipe found in the database.\nHere's a related suggestion:\n{ai_recipe}"
        return output_text
     
    
    if len(results[0])==1:
        recipes_titles=[row[0] for row in results if row and row[0]]
        output_text += f"Recipes: \n"
        output_text += "\n".join(f"- {t}" for t in recipes_titles)
    else:
        for ind,row in enumerate(results,start=1):
            if len(row)<2:continue
            recipes_title=user_query
            ingredients_json,directions_json=row[0],row[1]
            try:
                ingredients=ast.literal_eval(ingredients_json)
                if isinstance(ingredients, str):
                    ingredients = [ingredients]
            except:
                ingredients=[ingredients_json]
            try:
                directions=ast.literal_eval(directions_json)
                if isinstance(directions, str):
                    directions = [directions]
            except:
                directions=[directions_json]
            
            prompt = f"""
            You are a friendly chef.
            Rewrite the recipe "{recipes_title}" in a human-readable, easy-to-follow format.
            - Ingredients: {ingredients}
            - Instructions: {directions}
            
            Present ingredients as bullet points and instructions as numbered steps.
            """
            response=genai.GenerativeModel("gemini-2.0-flash").generate_content(prompt)
            result_recipe=response.text.strip()
            output_text += f"\n{result_recipe}\n"+"-"*50
    return output_text

# if __name__=="__main__":
#     print("Text-to-SQL \n")
#     while True:
#         user_input=input("Ask a question:").strip()
#         if user_input.lower()=="exit":
#             break
#         print("Question:\n",user_input)
#         sql_query=generate_sql(user_input)
#         print("SQL Query: \n",sql_query)
#         # res=execute_sql(sql_query)
#         # print("Results: ",res)
#         results=execute_sql(sql_query)
#         formatted_result=format_recipe_results(results,user_input)
#         print("\n"+formatted_result)

def get_response(user_input):
    sql_query=generate_sql(user_input)
    result=execute_sql(sql_query)
    formatted_result=format_recipe_results(result,user_input)
    return f"Sql Query:\n{sql_query}\n\nResult:{formatted_result}"

    
