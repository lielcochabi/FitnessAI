AI Fitness Plan Assistant

![CI](https://github.com/lielcochabi/FitnessAI/actions/workflows/ci.yml/badge.svg)

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

MONGODB_URI=your_mongodb_connection
RAPIDAPI_KEY=your_exercisedb_api_key
API_URL=http://localhost:8000

## Start the frontend
cd client
pip install -r requirements.txt
streamlit run main.py

If running locally, the client will open at:
http://localhost:8501

## Testing

The backend has a pytest suite (`server/test_*.py`) that runs against a real, throwaway MongoDB instead of a mock - see `server/conftest.py` for why.

Local setup (one-time):
```
docker run -d -p 27017:27017 mongo:7
cd server
cp .env.test.example .env.test
python -m venv venv
venv\Scripts\python.exe -m pip install -r requirements.txt pytest
```

Run the tests:
```
venv\Scripts\python.exe -m pytest -v
```

Tests will refuse to run (rather than silently falling back to the real database) if neither `MONGODB_URI` nor `server/.env.test` is set - see the comments at the top of `server/conftest.py`.

## Deployment

The project is designed to run in a containerized environment, and currently ships to production two different ways depending on the piece:

- **CI** - GitHub Actions (`.github/workflows/ci.yml`) runs the pytest suite and verifies both Dockerfiles still build, on every push and pull request.
- **Backend** - deployed on [Render](https://render.com), which watches this repo and redeploys automatically on push to `master` (see `render.yaml`).
- **Frontend** - deployed on Streamlit Community Cloud, same auto-deploy-on-push behavior.
- **Local / on-demand** - `docker compose up` runs the full stack (server + client) plus a Cloudflare Tunnel that exposes the local client at a temporary public URL for as long as it's running - useful for demoing without needing an always-on host.

The `deploy/` directory still holds Kubernetes manifests (Deployments, Services, and an Ingress built for a `k3d` cluster) from this project's original GitLab CI/CD pipeline, which deployed to a course-provided Kubernetes cluster. That cluster isn't reachable from here, so GitHub Actions doesn't have a `deploy` job - see Roadmap below.

## Project Structure
CLOUDPROG-LIEL-COCHABI
│
├── .github
│   └── workflows
│       └── ci.yml
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
│   ├── requirements.txt
│   ├── conftest.py
│   ├── test_database.py
│   ├── test_auth.py
│   ├── test_api.py
│   └── .env.test.example
│
├── .dockerignore
├── .gitignore
├── compose.yaml
└── README.md


## Technologies

Backend
Python, FastAPI, MongoDB

Frontend
Streamlit

Testing
pytest, GitHub Actions

Infrastructure
Docker, Kubernetes manifests (not currently deployed - see Deployment), Render, Streamlit Community Cloud, Cloudflare Tunnel (local/on-demand)

External API
ExerciseDB



## 12-Factor App Considerations

The project follows several principles from the 12-Factor App methodology:

Codebase
 - The project is stored in a Git repository, hosted on GitHub.

Dependencies
 - All dependencies are explicitly declared in requirements.txt.

Configuration
 - Configuration such as database connections and API keys are provided through environment variables.

Backing Services
 - MongoDB and ExerciseDB are treated as external services that the application connects to.

Build, Release, Run
 - GitHub Actions builds and tests the Docker images on every push; Render and Streamlit Community Cloud independently handle release/run by redeploying from the repo automatically.

Processes
 - The application runs inside containers - in production via Render/Streamlit Community Cloud, locally via `docker compose` or the Kubernetes manifests in `deploy/`.

Logs
 - Application logs are written to standard output and collected by the container runtime.

Dev/Prod Parity
 - Docker ensures the development and production environments behave consistently.

## Roadmap

 - **CI/CD deploy stage** - CI currently only tests and builds; there's no automated `deploy` job. The original GitLab pipeline deployed to a course-provided Kubernetes cluster that isn't reachable from here. Render/Streamlit Community Cloud cover this today via their own git integration, but a real GitHub Actions deploy job (e.g. pushing images to a registry and applying the `deploy/` manifests to a real cluster) is still an open item.