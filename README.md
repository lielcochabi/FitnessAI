AI Fitness Plan Assistant

## Motivation

Many people, including myself, want to start training, improve their workouts, or try new exercises. However, finding the right exercises or building an effective workout plan can take a long time and often becomes confusing.

This project was created to help solve this problem by using AI to suggest exercises and workout ideas that users may not have considered before.

The AI chatbot allows users to manage their workouts and provides information about specific exercises as well as general knowledge related to training and fitness.

## Concept 

The AI Fitness Plan Assistant is a cloud-native web application that allows users to interact with an AI fitness assistant through a chat interface.

The assistant can:
 - suggest exercises based on muscle groups or body parts
 - generate workout routines
 - answer fitness-related questions
 - allow users to save workout plans
 - allow users to save favorite exercises
 - store chat history

The application combines an AI language model with an exercise database API to provide structured and useful fitness recommendations.


## Architecture

The application follows a client–server architecture.

User requests are sent from the frontend interface to the backend API.
The backend processes the request, interacts with the AI model or external APIs when needed, and stores user data in the database.

## Architecture Flow

User
↓
Streamlit Frontend
↓
FastAPI Backend
├─ DSPy AI model
├─ MongoDB database
└─ ExerciseDB external APIx`

Components

Frontend
 - Streamlit
 - chat interface
 - user login/signup
 - workout plan management
 - favorite exercises management

Backend
 - FastAPI REST API
 - DSPy AI orchestration
 - exercise search logic
 - user data management

Database
 - MongoDB
 - stores users, workouts, favorites, and chat history

External API
 - ExerciseDB API
 - provides structured exercise data

## Running the project

## Start the Backend server
cd server
pip install -r requirements.txt
uvicorn main:app --reload

If running locally, the server will start at:
http://localhost:8000

The backend requires the following environment variables:

MONGO_URI=your_mongodb_connection
RAPIDAPI_KEY=your_exercisedb_api_key
API_URL=http://localhost:8000

## Start the frontend
cd client
pip install -r requirements.txt
streamlit run main.py

If running locally, the client will open at:
http://localhost:8501

## Deployment

The project is designed to run in a containerized environment.

The GitLab pipeline builds Docker images and deploys the application to a Kubernetes cluster using the manifests in the deploy directory.

The services are exposed through Kubernetes and can be accessed via the configured ingress.

## Project Structure
CLOUDPROG-LIEL-COCHABI
│
├── client
│   ├── pages
│   │   ├── ChatHistory.py
│   │   ├── Favorite_Exercises.py
│   │   └── Workout_Plans.py
│   ├── accountActions.py
│   ├── Dockerfile
│   ├── main.py
│   ├── requirements.txt
│   └── user_input.py
│
├── deploy
│   ├── deploymentClient.yaml
│   ├── deploymentServer.yaml
│   ├── project-ing.yaml
│   ├── service-client.yaml
│   └── service-server.yaml
│
├── server
│   ├── dataBase.py
│   ├── Dockerfile
│   ├── dspyRun.py
│   ├── exerciseDB.py
│   ├── main.py
│   └── requirements.txt
│
├── .dockerignore
├── .gitignore
├── .gitlab-ci.yml
├── compose.yaml
└── README.md


## Technologies

Backend
Python, FastAPI, MongoDB

Frontend
Streamlit

Infrastructure
Docker, Kubernetes, GitLab CI/CD

External API
ExerciseDB



## 12-Factor App Considerations

The project follows several principles from the 12-Factor App methodology:

Codebase
 - The project is stored in a Git repository and managed through GitLab.

Dependencies
 - All dependencies are explicitly declared in requirements.txt.

Configuration
 - Configuration such as database connections and API keys are provided through environment variables.

Backing Services
 - MongoDB and ExerciseDB are treated as external services that the application connects to.

Build, Release, Run
 - Docker images are built through GitLab CI/CD and deployed separately from the codebase.

Processes
 - The application runs inside containers managed by Kubernetes.

Logs
 - Application logs are written to standard output and collected by the container runtime.

Dev/Prod Parity
 - Docker ensures the development and production environments behave consistently.