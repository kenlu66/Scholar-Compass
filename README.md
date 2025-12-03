# Scholar Compass

An interactive web application for exploring academic research profiles. Scholar Compass visualizes collaboration networks, research topic evolution, and publication patterns of scholars using graph database technology and AI-powered analysis.

---

## 1. Project Structure

```text
Scholar Compass/
├── back_end/
│   └── rag.py                  # Flask backend server
├── webpage/
│   ├── index.html              # Frontend HTML
│   ├── app.js                  # JavaScript logic
│   └── figure/                 # Static assets
├── docker/
│   └── academic_graph_project/
│       ├── docker-compose.yml  # Neo4j configuration
│       ├── scripts/
│       │   └── init_database.py # Database initialization
│       └── neo4j_import/
│           └── concatenated.csv # Academic data
├── .env                        # Environment variables (create this)
├── requirements.txt            # Python dependencies
└── README.md                   # Project documentation
```

---

## 2. Features

### 2.1 Collaboration Network Visualization
Interactive graph showing co-authorship relationships.

### 2.2 Research Topics Evolution
Timeline view of research areas over the years.

### 2.3 Publication Venue Statistics
Analysis of publication outlets and preferences.

### 2.4 AI-Powered Analysis
Real-time streaming analysis of academic profiles using an LLM.

### 2.5 Graph Database Backend
Efficient querying with Neo4j for complex academic data.

---

## 3. Tech Stack

### 3.1 Frontend
- HTML5, CSS3  
- JavaScript (ES6+)  
- ECharts 5.4.3  

### 3.2 Backend
- Flask (Python)

### 3.3 Database
- Neo4j 5.15.0 (Graph Database)

### 3.4 LLM
- Alibaba Cloud Dashscope (Qwen-flash model)

### 3.5 Data
- OpenAlex academic dataset

---

## 4. Prerequisites

Before you begin, ensure you have the following installed:

1. Docker Desktop (for Neo4j database)  
2. Python 3.8 or higher  
3. `pip` (Python package manager)  

---

## 5. Installation

### 5.1 Install Python Dependencies

From the project root:

```bash
pip install -r requirements.txt
```

### 5.2 Set Up API Key (Required)

To use the AI analysis feature, you need an Alibaba Cloud Dashscope API key.

1. **Get your API key**
   - Visit Alibaba Cloud: <https://www.alibabacloud.com/en>  
   - Sign up or log in to your account  
   - Navigate to the API Keys section and create a new key  

2. **Create a `.env` file** in the project root directory with:

   ```bash
   DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   NEO4J_URI=bolt://localhost:7688
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=academic123
   ```

3. Replace `sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` with your actual API key.

> **Security notes**  
> - The `.env` file is already in `.gitignore` and will **not** be committed.  
> - Never share your API key publicly.  

### 5.3 Start Neo4j Database

Navigate to the Docker directory and start the Neo4j container:

```bash
cd docker/academic_graph_project
docker-compose up -d
```

Verify the container is running:

```bash
docker ps
```

You should see a container named `academic_graph` with status `healthy`.

**Neo4j Connection Details**

- Bolt Port: `7688` (for application connection)  
- Browser Port: `7475` (for web interface)  
- Username: `neo4j`  
- Password: `academic123`  
- Web Interface: <http://localhost:7475>  

### 5.4 Initialize Database (First Time Only)

If starting with a fresh database, import the academic data:

```bash
cd docker/academic_graph_project
python3 scripts/init_database.py
```

This script will:

- Create database constraints and indexes  
- Import papers, authors, topics, and venues  
- Create collaboration relationships  

> Note: The import process may take several minutes depending on dataset size.

---

## 6. Running the Application

### 6.1 Start the Backend Server

From the project root directory:

```bash
python3 back_end/rag.py
```

You should see output similar to:

```text
Successfully connected to Neo4j: bolt://localhost:7688
Starting Scholar Compass Backend...
Running on http://0.0.0.0:5001
```

Keep this terminal window open — the backend must remain running.

### 6.2 Access the Application

Open your web browser and navigate to:

<http://localhost:5001>

---

## 8. Usage

### 8.1 Enter a Professor's Name

Type a scholar's name in the search box (e.g., `Wei Xu`).

### 8.2 View Visualizations

Three interactive charts will display:

- Collaboration Network (left)  
- Research Topics Evolution (center)  
- Publication Venues (right)  

### 8.3 Read AI Analysis

Real-time streaming analysis appears above the charts.

### 8.4 Start New Search

Click **“Start New Conversation”** to search for another scholar.
