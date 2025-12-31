from flask import Flask, render_template, request, jsonify, Response, stream_with_context
from flask_cors import CORS
from openai import OpenAI
from neo4j import GraphDatabase
from dotenv import load_dotenv
import time
import os
import json

load_dotenv()

app = Flask(__name__,
            static_folder='../webpage',
            static_url_path='',
            template_folder='../webpage')
CORS(app)

client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY", "INPUT YOUR API KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7688")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "academic123")

driver = None
try:
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    print(f"Successfully connected to Neo4j: {NEO4J_URI}")
except Exception as e:
    print(f"Neo4j connection failed: {e}")


def close_driver():
    if driver:
        driver.close()


def run_cypher_query(query, params=None):
    if not driver:
        print("[Error] Database driver not connected")
        return []

    with driver.session() as session:
        result = session.run(query, params or {})
        return [record.data() for record in result]


def has_invalid_characters(name):
    if not name:
        return True
    invalid_chars = ['?', '\ufffd', '\\', '\x00']
    return any(char in name for char in invalid_chars)


def _get_author_id_by_name(scholar_name: str):
    query = """
    MATCH (a:Author)
    WHERE toLower(a.display_name) CONTAINS toLower($name)
    RETURN a.id as id, a.display_name as name, a.pagerank as pagerank
    ORDER BY size(a.display_name) ASC, a.pagerank DESC
    LIMIT 1
    """
    results = run_cypher_query(query, {"name": scholar_name})
    if results:
        return results[0]
    return None


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/visuals/collaboration-network', methods=['POST'])
def get_collaboration_network():
    print("Fetching collaboration network data")
    try:
        data = request.json
        query_name = data.get('query')

        author = _get_author_id_by_name(query_name)
        if not author:
            return jsonify({'error': 'Scholar not found'}), 404

        author_id = author['id']
        author_name = author['name']

        cypher = """
        MATCH (a:Author {id: $id})-[:AUTHORED]->(p:Paper)<-[:AUTHORED]-(co:Author)
        WHERE a.id <> co.id
        WITH co, count(p) as weight, sum(p.cited_by_count) as total_citations
        ORDER BY weight DESC
        LIMIT 20
        RETURN co.id as id, co.display_name as name, weight, total_citations
        """
        results = run_cypher_query(cypher, {"id": author_id})

        nodes = []
        edges = []

        nodes.append({
            "id": author_id,
            "name": author_name,
            "symbolSize": 30,
            "category": 0,
            "draggable": True
        })

        for row in results:
            if has_invalid_characters(row['name']):
                continue

            nodes.append({
                "id": row['id'],
                "name": row['name'],
                "symbolSize": 10 + (row['weight'] * 2),
                "category": 1,
                "value": row['weight']
            })
            edges.append({
                "source": author_id,
                "target": row['id'],
                "value": row['weight']
            })

        return jsonify({
            'success': True,
            'data': {
                'nodes': nodes,
                'edges': edges,
                'center_scholar': author_name
            }
        })

    except Exception as e:
        print(f"Error in collaboration-network: {e}")
        return jsonify({'error': str(e), 'success': False}), 500


@app.route('/api/visuals/topic-evolution', methods=['POST'])
def get_topic_evolution():
    print("Fetching topic evolution data")
    try:
        data = request.json
        query_name = data.get('query')

        author = _get_author_id_by_name(query_name)
        if not author:
            return jsonify({'error': 'Scholar not found'}), 404

        cypher = """
        MATCH (a:Author {id: $id})-[:AUTHORED]->(p:Paper)-[:IN_SUBFIELD]->(s:Subfield)
        WHERE p.publication_year IS NOT NULL
        WITH p.publication_year as year, s.display_name as topic, count(p) as count
        ORDER BY year ASC, count DESC
        RETURN year, topic, count
        """
        results = run_cypher_query(cypher, {"id": author['id']})

        return jsonify({
            'success': True,
            'data': results
        })

    except Exception as e:
        print(f"Error in topic-evolution: {e}")
        return jsonify({'error': str(e), 'success': False}), 500


@app.route('/api/visuals/venue-stats', methods=['POST'])
def get_venue_stats():
    print("Fetching venue statistics data")
    try:
        data = request.json
        query_name = data.get('query')

        author = _get_author_id_by_name(query_name)
        if not author:
            return jsonify({'error': 'Scholar not found'}), 404

        author_id = author['id']

        top_venues_cypher = """
        MATCH (a:Author {id: $id})-[:AUTHORED]->(p:Paper)-[:PUBLISHED_IN]->(so:Source)
        RETURN so.display_name as venue, count(p) as count
        ORDER BY count DESC
        LIMIT 10
        """
        top_venues = run_cypher_query(top_venues_cypher, {"id": author_id})

        dist_cypher = """
        MATCH (a:Author {id: $id})-[:AUTHORED]->(p:Paper)-[:PUBLISHED_IN]->(so:Source)
        WHERE so.type IS NOT NULL
        RETURN so.type as type, count(p) as count
        """
        distribution = run_cypher_query(dist_cypher, {"id": author_id})

        top5_ids_cypher = """
        MATCH (a:Author {id: $id})-[:AUTHORED]->(p:Paper)-[:PUBLISHED_IN]->(so:Source)
        RETURN so.id as sid, count(p) as c ORDER BY c DESC LIMIT 5
        """
        top5_ids = [r['sid'] for r in run_cypher_query(top5_ids_cypher, {"id": author_id})]

        trends = []
        if top5_ids:
            trends_cypher = """
            MATCH (a:Author {id: $id})-[:AUTHORED]->(p:Paper)-[:PUBLISHED_IN]->(so:Source)
            WHERE so.id IN $top_ids AND p.publication_year >= 2015
            RETURN so.display_name as venue, p.publication_year as year, count(p) as count
            ORDER BY year ASC
            """
            trends = run_cypher_query(trends_cypher, {"id": author_id, "top_ids": top5_ids})

        return jsonify({
            'success': True,
            'data': {
                'top_venues': top_venues,
                'distribution': distribution,
                'trends': trends
            }
        })

    except Exception as e:
        print(f"Error in venue-stats: {e}")
        return jsonify({'error': str(e), 'success': False}), 500


@app.route('/api/analyze', methods=['POST'])
def analyze_scholar():
    print("/api/analyze called")
    try:
        data = request.json
        scholar_name = data.get('scholar_name')
        network_data = data.get('network_data')
        topic_data = data.get('topic_data')
        venue_data = data.get('venue_data')

        if not scholar_name:
            return jsonify({'error': 'Scholar name is required'}), 400

        analysis_prompt = f"""Analyze the academic research profile of Professor {scholar_name} based on the following data:

Collaboration Network:
Total collaborators: {len(network_data.get('nodes', [])) - 1}
Top 5 collaborators: {', '.join([n['name'] for n in network_data.get('nodes', [])[1:6]])}
Collaboration intensity: Average {sum([e['value'] for e in network_data.get('edges', [])]) / max(len(network_data.get('edges', [])), 1):.1f} papers per collaborator

Research Topics Evolution:
Research areas covered: {len(set([d['topic'] for d in topic_data]))} distinct topics
Most active research topics: {', '.join(list(set([d['topic'] for d in sorted(topic_data, key=lambda x: x['count'], reverse=True)[:5]])))}
Publication timeline: {min([d['year'] for d in topic_data if d['year']])} - {max([d['year'] for d in topic_data if d['year']])}

Publication Venues:
Top publication venues: {', '.join([v['venue'] for v in venue_data.get('top_venues', [])[:5]])}
Total venues used: {len(venue_data.get('top_venues', []))}

Please provide a comprehensive analysis covering:
1. Research Collaboration Patterns: Analyze the collaboration network and identify key research partnerships.
2. Research Topic Evolution: Describe how the scholar's research interests have evolved over time and identify any major shifts or trends.
3. Publication Strategy: Evaluate the scholar's publishing venues and what this reveals about their academic impact.
4. Overall Academic Profile: Provide an integrated summary of the scholar's research trajectory, strengths, and current research focus.

Keep the analysis professional, data-driven, and concise (approximately 300-400 words)."""

        def generate():
            try:
                stream = client.chat.completions.create(
                    model="qwen-plus",
                    messages=[
                        {"role": "system", "content": "You are an expert academic analyst specializing in evaluating research profiles and scholarly impact."},
                        {"role": "user", "content": analysis_prompt}
                    ],
                    temperature=0.7,
                    stream=True
                )

                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        yield f"data: {json.dumps({'content': content})}\n\n"

                yield f"data: {json.dumps({'done': True})}\n\n"

            except Exception as e:
                print(f"Error in stream: {e}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return Response(stream_with_context(generate()),
                       mimetype='text/event-stream',
                       headers={
                           'Cache-Control': 'no-cache',
                           'X-Accel-Buffering': 'no'
                       })

    except Exception as e:
        print(f"Error in analyze_scholar: {e}")
        return jsonify({'error': str(e), 'success': False}), 500


@app.route('/api/qanda', methods=['POST'])
def qanda():
    print("/api/qanda called")
    try:
        data = request.json
        scholar_name = data.get('scholar_name')
        user_question = data.get('question')

        if not scholar_name or not user_question:
            return jsonify({'error': 'Required fields missing'}), 400

        author = _get_author_id_by_name(scholar_name)
        if not author:
            return jsonify({'success': True, 'llm_answer': "Sorry, I could not find this scholar in the database."})

        papers_cypher = """
        MATCH (a:Author {id: $id})-[:AUTHORED]->(p:Paper)
        RETURN p.title as title, p.cited_by_count as cites
        ORDER BY cites DESC LIMIT 5
        """
        papers = run_cypher_query(papers_cypher, {"id": author['id']})

        topics_cypher = """
        MATCH (a:Author {id: $id})-[:AUTHORED]->(p:Paper)-[:IN_SUBFIELD]->(s:Subfield)
        RETURN s.display_name as topic, count(p) as c ORDER BY c DESC LIMIT 5
        """
        topics = run_cypher_query(topics_cypher, {"id": author['id']})

        context_str = f"Scholar: {author['name']}\n"
        context_str += f"Top Papers: {'; '.join([p['title'] for p in papers])}\n"
        context_str += f"Top Research Topics: {', '.join([t['topic'] for t in topics])}\n"

        system_prompt = "You are Scholar Compass. Answer based on the context below."
        final_prompt = f"{system_prompt}\nCONTEXT:\n{context_str}\n\nUser Question: {user_question}"

        completion = client.chat.completions.create(
            model="qwen-plus",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": final_prompt}
            ],
            temperature=0.7
        )

        return jsonify({
            'success': True,
            'llm_answer': completion.choices[0].message.content
        })

    except Exception as e:
        print(f"Error in qanda: {e}")
        return jsonify({'error': str(e), 'success': False}), 500


if __name__ == '__main__':
    print("Starting Scholar Compass Backend")
    try:
        app.run(debug=True, host='0.0.0.0', port=5001)
    finally:
        close_driver()