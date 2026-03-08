# stocker
Stock sentiment analysis by stalking web articles/discussion


1. run frontend
cd frontend
npm run dev 

2. run backend
dont cd, just make sure ur root folder is stocker
docker-compose up --build

misc
testing the scraper api
- POST http://localhost:8000/api/ticker 
(get something like this)

{
    "status": "processing",
    "task_id": "6b3b8f60272845a2bee09edf9fa89d09"
}
and then paste the task id into the next get request like this:
http://localhost:8000/api/status/06235b86cf894e93b0d9a96c2fe74603

