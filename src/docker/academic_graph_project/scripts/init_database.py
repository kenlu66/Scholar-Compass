from neo4j import GraphDatabase
import time
import os
import sys

print("=== Starting database initialization ===")

def wait_for_neo4j():
    print("Waiting for Neo4j to start...")
    for i in range(30):
        time.sleep(1)
    print("Waiting completed")

def init_database():
    uri = "bolt://localhost:7688"
    user = "neo4j"
    password = "academic123"
    
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        
        with driver.session() as session:
            result = session.run("RETURN 1 as test")
            print("✓ Database connection successful")
            
        with driver.session() as session:
            print("Creating indexes and constraints...")
            
            constraints = [
                "CREATE CONSTRAINT UniqueWorkIdConstraint FOR (p:Paper) REQUIRE p.id IS UNIQUE",
                "CREATE CONSTRAINT UniqueAuthorIdConstraint FOR (a:Author) REQUIRE a.id IS UNIQUE", 
                "CREATE CONSTRAINT UniqueSubfieldIdConstraint FOR (s:Subfield) REQUIRE s.id IS UNIQUE",
                "CREATE CONSTRAINT UniqueFieldIdConstraint FOR (f:Field) REQUIRE f.id IS UNIQUE",
                "CREATE CONSTRAINT UniqueSourceIdConstraint FOR (so:Source) REQUIRE so.id IS UNIQUE"
            ]
            
            indexes = [
                "CREATE INDEX PaperTitleIndex FOR (p:Paper) ON (p.title)",
                "CREATE INDEX PaperPublicationYearIndex FOR (p:Paper) ON (p.publication_year)", 
                "CREATE INDEX PaperFWCIIndex FOR (p:Paper) ON (p.fwci)"
            ]
            
            for constraint in constraints:
                session.run(constraint)
            
            for index in indexes:
                session.run(index)
                
            print("✓ Indexes and constraints created successfully")
            
            print("Importing paper data...")
            session.run("""
                LOAD CSV WITH HEADERS FROM 'file:///concatenated.csv' AS row 
                WITH row WHERE row.id IS NOT NULL AND row.id <> '' 
                MERGE (p:Paper {id: row.id})
                SET 
                  p.title = row.title,
                  p.publication_year = toInteger(row.publication_year),
                  p.fwci = toFloat(row.fwci),
                  p.cited_by_count = toInteger(row.cited_by_count),
                  p.citation_normalized_percentile = toFloat(row.`citation_normalized_percentile.value`),
                  p.is_in_top_1_percent = row.`citation_normalized_percentile.is_in_top_1_percent` = 'TRUE',
                  p.is_in_top_10_percent = row.`citation_normalized_percentile.is_in_top_10_percent` = 'TRUE'
            """)
            print("✓ Paper data imported successfully")
            
            print("Importing research topic hierarchy...")
            session.run("""
                LOAD CSV WITH HEADERS FROM 'file:///concatenated.csv' AS row
                WITH row WHERE row.`primary_topic.subfield.id` IS NOT NULL AND row.`primary_topic.subfield.id` <> ''
                MERGE (s:Subfield {id: row.`primary_topic.subfield.id`})
                SET s.display_name = row.`primary_topic.subfield.display_name`

                WITH s, row
                MATCH (p:Paper {id: row.id})
                MERGE (p)-[:IN_SUBFIELD]->(s)
            """)
            
            session.run("""
                LOAD CSV WITH HEADERS FROM 'file:///concatenated.csv' AS row
                WITH row WHERE row.`primary_topic.field.id` IS NOT NULL AND row.`primary_topic.field.id` <> ''
                MERGE (f:Field {id: row.`primary_topic.field.id`})
                SET f.display_name = row.`primary_topic.field.display_name`

                WITH f, row
                MATCH (s:Subfield {id: row.`primary_topic.subfield.id`})
                MERGE (s)-[:PART_OF_FIELD]->(f)
            """)
            print("✓ Research topic hierarchy imported successfully")
            
            print("Importing source nodes...")
            session.run("""
                LOAD CSV WITH HEADERS FROM 'file:///concatenated.csv' AS row
                WITH row WHERE row.`primary_location.source.id` IS NOT NULL AND row.`primary_location.source.id` <> ''
                MERGE (so:Source {id: row.`primary_location.source.id`})
                SET 
                  so.display_name = row.`primary_location.source.display_name`,
                  so.type = row.`primary_location.source.type`

                WITH so, row
                MATCH (p:Paper {id: row.id})
                MERGE (p)-[:PUBLISHED_IN]->(so)
            """)
            print("✓ Source nodes imported successfully")
            
            print("Importing authors...")
            session.run("""
                LOAD CSV WITH HEADERS FROM 'file:///concatenated.csv' AS row
                WITH row,
                     split(replace(replace(replace(row.`authorships.author.id`, '[', ''), ']', ''), '"', ''), ',') AS authorIds,
                     split(replace(replace(replace(row.`authorships.author.display_name`, '[', ''), ']', ''), '"', ''), ',') AS authorNames
                WHERE size(authorIds) > 0 AND authorIds[0] <> ''

                UNWIND range(0, size(authorIds)-1) AS index
                WITH trim(authorIds[index]) AS authorId, trim(authorNames[index]) AS authorName
                WHERE authorId <> ''

                MERGE (a:Author {id: authorId})
                SET a.display_name = authorName
            """)
            print("✓ Authors imported successfully")

            print("Creating author-paper relationships...")
            session.run("""
                LOAD CSV WITH HEADERS FROM 'file:///concatenated.csv' AS row
                CALL {
                    WITH row
                    WITH row, split(replace(replace(replace(row.`authorships.author.id`, '[', ''), ']', ''), '"', ''), ',') AS authorIds
                    WHERE size(authorIds) > 0 AND authorIds[0] <> ''

                    UNWIND range(0, size(authorIds)-1) AS index
                    WITH row, trim(authorIds[index]) AS authorId, index
                    WHERE authorId <> ''

                    MATCH (a:Author {id: authorId}), (p:Paper {id: row.id})
                    MERGE (a)-[:AUTHORED {authorship_order: index + 1}]->(p)
                } IN TRANSACTIONS OF 1000 ROWS
            """)
            print("✓ Author-paper relationships created successfully")
            
            print("\nData statistics:")
            node_types = ['Paper', 'Author', 'Field', 'Subfield', 'Source']
            for node_type in node_types:
                result = session.run(f"MATCH (n:{node_type}) RETURN count(n) as count")
                count = result.single()["count"]
                print(f"  {node_type}: {count} nodes")
            
            print("✓ Database initialization completed successfully!")
            
    except Exception as e:
        print(f"!!! Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'driver' in locals():
            driver.close()

if __name__ == "__main__":
    wait_for_neo4j()
    init_database()
    print("=== Script execution completed ===")