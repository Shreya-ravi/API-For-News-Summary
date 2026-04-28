# API-For-News-Summary
A FastAPI-based web application that extracts news articles from URLs, generates multilingual summaries, and creates shareable short links.

## 🚀 Live Demo

🌍 **Deployed API:** https://your-app-url  
📄 **Swagger Docs:** https://your-app-url/docs  

---

## 🚀 Features

- 🔗 Extracts full article content from any news URL  
- ✂️ Generates concise summaries (English + original language)  
- 🌐 Supports multilingual translation  
- 🏷️ Generates SEO-friendly slugs & keywords  
- 🔗 Creates short URLs for easy sharing  
- 📄 Stores articles using a database  
- 🌍 Provides REST API + Web UI  

---

## 🛠️ Tech Stack

- **Backend:** FastAPI  
- **Database:** SQLite (dev) → PostgreSQL (recommended for production)  
- **ORM:** SQLAlchemy  
- **Frontend:** HTML, CSS (Jinja2 Templates)  

---

## ⚙️ Run Locally


git clone https://github.com/your-username/your-repo-name.git
cd your-repo-name
pip install -r requirements.txt
uvicorn main:app --reload

Open:

http://localhost:8000
http://localhost:8000/docs


## 🌐 Deployment (Railway)


Push code to GitHub
Go to Railway
Create New Project → Deploy from GitHub

# Add Start Command:
uvicorn main:app --host 0.0.0.0 --port 8000

# Add requirements.txt


Deploy 🚀
# 🔌 API Endpoints
Health Check
GET /api/health
Summarize Article
POST /api/summarize
Get Article
GET /api/article/{code}

# 📸 Screenshots

(Add your UI screenshots here)

# ⚠️ Notes
Demo login system is used
SQLite used for development
Can be extended with caching, auth, and scaling

# 🚀 Future Improvements
JWT Authentication
Redis caching
Rate limiting
Docker deployment


# 📌 Conclusion

This project demonstrates a real-world backend system combining web scraping, NLP, API development, and database management using FastAPI.
