import sqlite3
import json
import uuid
import numpy as np
import os
from datetime import datetime
from config import DB_PATH

class VectorStore:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        """Initialize the database tables for documents, vectorized chunks, users, sessions, chat_sessions, and questions."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Table 1: Documents metadata with chatbot_id
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            chatbot_id TEXT NOT NULL DEFAULT 'default',
            filename TEXT NOT NULL,
            file_size INTEGER NOT NULL,
            chunk_count INTEGER NOT NULL,
            uploaded_at TEXT NOT NULL
        )
        """)

        # Schema migration: Add chatbot_id if table exists but doesn't have it
        try:
            cursor.execute("ALTER TABLE documents ADD COLUMN chatbot_id TEXT DEFAULT 'default'")
        except sqlite3.OperationalError:
            pass # Column already exists

        # Table 2: Chunks and embeddings
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            id TEXT PRIMARY KEY,
            document_id TEXT,
            chunk_index INTEGER NOT NULL,
            text TEXT NOT NULL,
            embedding BLOB NOT NULL,
            FOREIGN KEY (document_id) REFERENCES documents (id) ON DELETE CASCADE
        )
        """)

        # Schema migration: Drop old users table if it still has username column
        try:
            cursor.execute("SELECT email FROM users LIMIT 1")
        except sqlite3.OperationalError:
            # Table doesn't have email column, let's migrate by dropping old tables
            cursor.execute("DROP TABLE IF EXISTS sessions")
            cursor.execute("DROP TABLE IF EXISTS users")

        # Table 3: Users metadata
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            chatbot_id TEXT UNIQUE NOT NULL,
            api_key TEXT DEFAULT '',
            settings_json TEXT DEFAULT '{}',
            created_at TEXT NOT NULL
        )
        """)

        # Migration: Ensure settings_json column exists
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN settings_json TEXT DEFAULT '{}'")
        except sqlite3.OperationalError:
            pass


        # Table 4: User login sessions (auth tokens)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            chatbot_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
        """)

        # Table 5: Chat sessions (conversation threads)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            chatbot_id TEXT NOT NULL,
            title TEXT NOT NULL DEFAULT 'New Chat',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
        """)

        # Table 6: Questions within chat sessions
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            chatbot_id TEXT NOT NULL,
            question TEXT NOT NULL,
            question_type TEXT NOT NULL DEFAULT 'document',
            ai_response TEXT DEFAULT '',
            admin_response TEXT DEFAULT '',
            source TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'new',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES chat_sessions (id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
        """)

        # Ensure user_email column exists for external inquiries
        try:
            cursor.execute("SELECT user_email FROM questions LIMIT 1")
        except sqlite3.OperationalError:
            try:
                cursor.execute("ALTER TABLE questions ADD COLUMN user_email TEXT DEFAULT ''")
            except Exception:
                pass

        conn.commit()
        conn.close()

    # --- Document Methods ---

    def add_document(self, doc_id, filename, file_size, chunk_count, chatbot_id="default"):
        """Register an uploaded document."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        uploaded_at = datetime.now().isoformat()
        
        # Remove any existing document with same ID to prevent constraint errors
        cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        
        cursor.execute(
            "INSERT INTO documents (id, chatbot_id, filename, file_size, chunk_count, uploaded_at) VALUES (?, ?, ?, ?, ?, ?)",
            (doc_id, chatbot_id, filename, file_size, chunk_count, uploaded_at)
        )
        conn.commit()
        conn.close()

    def add_chunks(self, doc_id, chunks_data):
        """
        Store text chunks and their embeddings.
        chunks_data list of dicts: {'text': str, 'embedding': list[float], 'index': int}
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for chunk in chunks_data:
            chunk_id = f"{doc_id}_{chunk['index']}"
            # Convert embedding to float32 binary blob
            emb_array = np.array(chunk['embedding'], dtype=np.float32)
            emb_blob = emb_array.tobytes()
            
            cursor.execute(
                "INSERT INTO chunks (id, document_id, chunk_index, text, embedding) VALUES (?, ?, ?, ?, ?)",
                (chunk_id, doc_id, chunk['index'], chunk['text'], emb_blob)
            )
            
        conn.commit()
        conn.close()

    def delete_document(self, doc_id, chatbot_id=None):
        """Remove document and its vector representations, with optional ownership validation."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        cursor = conn.cursor()
        if chatbot_id:
            cursor.execute("SELECT 1 FROM documents WHERE id = ? AND chatbot_id = ?", (doc_id, chatbot_id))
            if not cursor.fetchone():
                conn.close()
                raise ValueError("Unauthorized: Document does not belong to your chatbot.")
        cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        conn.commit()
        conn.close()

    def get_documents(self, chatbot_id=None):
        """Get list of active documents, optionally filtered by a specific chatbot."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        if chatbot_id:
            cursor.execute("SELECT id, filename, file_size, chunk_count, uploaded_at FROM documents WHERE chatbot_id = ? ORDER BY uploaded_at DESC", (chatbot_id,))
        else:
            cursor.execute("SELECT id, filename, file_size, chunk_count, uploaded_at FROM documents ORDER BY uploaded_at DESC")
        rows = cursor.fetchall()
        conn.close()
        
        docs = []
        for r in rows:
            docs.append({
                "id": r[0],
                "filename": r[1],
                "file_size": r[2],
                "chunk_count": r[3],
                "uploaded_at": r[4]
            })
        return docs

    def get_stats(self, chatbot_id="default"):
        """Retrieve database statistics for a specific chatbot."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM documents WHERE chatbot_id = ?", (chatbot_id,))
        doc_count = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM chunks c
            JOIN documents d ON c.document_id = d.id
            WHERE d.chatbot_id = ?
        """, (chatbot_id,))
        chunk_count = cursor.fetchone()[0]
        
        conn.close()
        
        db_size = 0
        if os.path.exists(self.db_path):
            db_size = os.path.getsize(self.db_path)
            
        return {
            "document_count": doc_count,
            "chunk_count": chunk_count,
            "db_size_bytes": db_size
        }

    def search_similar_chunks(self, query_embedding, chatbot_id="default", limit=5):
        """
        Find top matches using cosine similarity in NumPy, filtered by chatbot_id.
        Returns list of dicts: {'text': str, 'filename': str, 'score': float}
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Join chunks with documents to get filenames, filtered by chatbot_id
        cursor.execute("""
            SELECT c.text, c.embedding, d.filename, c.chunk_index
            FROM chunks c
            JOIN documents d ON c.document_id = d.id
            WHERE d.chatbot_id = ?
        """, (chatbot_id,))
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return []

        query_vector = np.array(query_embedding, dtype=np.float32)
        q_norm = np.linalg.norm(query_vector)
        if q_norm == 0:
            return []

        results = []
        for text, emb_blob, filename, idx in rows:
            # Reconstruct numpy array from float32 blob
            chunk_vector = np.frombuffer(emb_blob, dtype=np.float32)
            if chunk_vector.shape != query_vector.shape:
                continue
            
            # Compute cosine similarity
            c_norm = np.linalg.norm(chunk_vector)
            if c_norm == 0:
                continue

                
            similarity = np.dot(chunk_vector, query_vector) / (c_norm * q_norm)
            
            results.append({
                "text": text,
                "filename": filename,
                "chunk_index": idx,
                "score": float(similarity)
            })

        # Sort by similarity score descending
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    # --- User Management Methods ---

    def create_user(self, user_id, email, password_hash, chatbot_id):
        """Insert a new user into the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        created_at = datetime.now().isoformat()
        cursor.execute(
            "INSERT INTO users (id, email, password_hash, chatbot_id, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, email, password_hash, chatbot_id, created_at)
        )
        conn.commit()
        conn.close()

    def get_user_by_email(self, email):
        """Retrieve user details by email."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id, email, password_hash, chatbot_id, api_key FROM users WHERE email = ?", (email,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_user_by_id(self, user_id):
        """Retrieve user details by user ID including multi-provider settings."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id, email, password_hash, chatbot_id, api_key, settings_json FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        res = dict(row)
        try:
            res["settings"] = json.loads(res.get("settings_json") or "{}")
        except Exception:
            res["settings"] = {}
        return res

    def get_user_by_chatbot_id(self, chatbot_id):
        """Retrieve user details by chatbot ID including multi-provider settings."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id, email, chatbot_id, api_key, settings_json FROM users WHERE chatbot_id = ?", (chatbot_id,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        res = dict(row)
        try:
            res["settings"] = json.loads(res.get("settings_json") or "{}")
        except Exception:
            res["settings"] = {}
        return res

    def update_user_api_key(self, user_id, api_key):
        """Update the API key for a user (backward compatible)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET api_key = ? WHERE id = ?", (api_key, user_id))
        conn.commit()
        conn.close()

    def update_user_settings(self, user_id, settings_dict):
        """Update full provider settings for a user."""
        user = self.get_user_by_id(user_id)
        current_settings = user.get("settings", {}) if user else {}
        current_settings.update(settings_dict)

        # Determine the active provider key to sync into the api_key column
        active_provider = current_settings.get("provider", "").lower()
        active_key = ""
        if active_provider == "openai":
            active_key = current_settings.get("openai_key", "")
        elif active_provider in ("claude", "anthropic"):
            active_key = current_settings.get("claude_key", "") or current_settings.get("anthropic_key", "")
        elif active_provider in ("generic", "custom"):
            active_key = current_settings.get("generic_key", "")
        elif active_provider == "groq":
            active_key = current_settings.get("groq_key", "") or current_settings.get("generic_key", "")
        elif active_provider == "openrouter":
            active_key = current_settings.get("openrouter_key", "") or current_settings.get("generic_key", "")

        # Fall back to gemini key if no provider-specific key resolved
        if not active_key:
            active_key = current_settings.get("gemini_key", "") or current_settings.get("api_key", "")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        if active_key:
            cursor.execute(
                "UPDATE users SET settings_json = ?, api_key = ? WHERE id = ?",
                (json.dumps(current_settings), active_key, user_id)
            )
        else:
            cursor.execute(
                "UPDATE users SET settings_json = ? WHERE id = ?",
                (json.dumps(current_settings), user_id)
            )
        conn.commit()
        conn.close()
        return current_settings

    def get_user_provider_key(self, user_info, provider="gemini"):
        """Get the specific API key for the requested provider from user record."""
        if not user_info:
            return ""
        settings = user_info.get("settings", {})
        prov = (provider or "gemini").lower()

        # Check provider specific keys in settings
        if prov == "gemini":
            return settings.get("gemini_key") or user_info.get("api_key") or ""
        elif prov == "openai":
            return settings.get("openai_key") or ""
        elif prov in ("claude", "anthropic"):
            return settings.get("claude_key") or settings.get("anthropic_key") or ""
        elif prov in ("generic", "custom"):
            return settings.get("generic_key") or settings.get("custom_key") or settings.get("openai_key") or ""
        elif prov == "groq":
            return settings.get("groq_key") or settings.get("generic_key") or ""
        elif prov == "openrouter":
            return settings.get("openrouter_key") or settings.get("generic_key") or ""
        return user_info.get("api_key", "")


    def validate_chatbot_id(self, chatbot_id):
        """Check if a chatbot ID belongs to a registered user."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM users WHERE chatbot_id = ?", (chatbot_id,))
        row = cursor.fetchone()
        conn.close()
        return row is not None

    # --- Auth Session Management Methods ---

    def create_session(self, token, user_id, chatbot_id, expires_at):
        """Save a new active login session."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        created_at = datetime.now().isoformat()
        cursor.execute(
            "INSERT INTO sessions (token, user_id, chatbot_id, created_at, expires_at) VALUES (?, ?, ?, ?, ?)",
            (token, user_id, chatbot_id, created_at, expires_at)
        )
        conn.commit()
        conn.close()

    def get_session(self, token):
        """Fetch session information by token."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT token, user_id, chatbot_id, expires_at FROM sessions WHERE token = ?", (token,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def delete_session(self, token):
        """Delete/revoke an active session."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()
        conn.close()

    # --- Chat Session Management Methods ---

    def create_chat_session(self, session_id, user_id, chatbot_id, title="New Chat"):
        """Create a new chat session (conversation thread)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute(
            "INSERT INTO chat_sessions (id, user_id, chatbot_id, title, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (session_id, user_id, chatbot_id, title, now, now)
        )
        conn.commit()
        conn.close()

    def get_chat_sessions(self, user_id, chatbot_id):
        """Get all chat sessions for a user, ordered by most recent activity."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            """SELECT cs.id, cs.title, cs.created_at, cs.updated_at,
                      (SELECT COUNT(*) FROM questions q WHERE q.session_id = cs.id) as question_count
               FROM chat_sessions cs
               WHERE cs.user_id = ? AND cs.chatbot_id = ?
               ORDER BY cs.updated_at DESC""",
            (user_id, chatbot_id)
        )
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_chat_session_by_id(self, session_id):
        """Retrieve a single chat session by ID."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id, user_id, chatbot_id, title, created_at, updated_at FROM chat_sessions WHERE id = ?", (session_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def update_chat_session_title(self, session_id, title):
        """Update the title of a chat session."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute(
            "UPDATE chat_sessions SET title = ?, updated_at = ? WHERE id = ?",
            (title, now, session_id)
        )
        conn.commit()
        conn.close()

    def touch_chat_session(self, session_id):
        """Update the updated_at timestamp of a chat session."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute(
            "UPDATE chat_sessions SET updated_at = ? WHERE id = ?",
            (now, session_id)
        )
        conn.commit()
        conn.close()

    def delete_chat_session(self, session_id, user_id):
        """Delete a chat session and all its questions."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM questions WHERE session_id = ? AND user_id = ?", (session_id, user_id))
        cursor.execute("DELETE FROM chat_sessions WHERE id = ? AND user_id = ?", (session_id, user_id))
        conn.commit()
        conn.close()

    def admin_delete_chat_session(self, session_id, chatbot_id):
        """Admin: Delete a chat session and all its questions by chatbot_id."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM questions WHERE session_id = ? AND chatbot_id = ?", (session_id, chatbot_id))
        cursor.execute("DELETE FROM chat_sessions WHERE id = ? AND chatbot_id = ?", (session_id, chatbot_id))
        conn.commit()
        conn.close()

    def admin_delete_question(self, question_id, chatbot_id):
        """Admin: Delete a single question/inquiry by id and chatbot_id."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        cursor = conn.cursor()
        cursor.execute("SELECT session_id, question_type FROM questions WHERE id = ? AND chatbot_id = ?", (question_id, chatbot_id))
        row = cursor.fetchone()
        if not row:
            conn.close()
            raise ValueError("Question not found or access denied.")
        session_id, q_type = row[0], row[1]

        cursor.execute("DELETE FROM questions WHERE id = ? AND chatbot_id = ?", (question_id, chatbot_id))

        # If it was an inquiry session created via add_widget_inquiry, check if any questions left in that session
        if session_id:
            cursor.execute("SELECT COUNT(*) FROM questions WHERE session_id = ?", (session_id,))
            remaining = cursor.fetchone()[0]
            if remaining == 0 and q_type == 'inquiry':
                cursor.execute("DELETE FROM chat_sessions WHERE id = ? AND chatbot_id = ?", (session_id, chatbot_id))

        conn.commit()
        conn.close()

    # --- Question Management Methods ---

    def add_question(self, question_id, session_id, user_id, chatbot_id, question, question_type="document",
                     ai_response="", source="", status="new", user_email=""):
        """Store a new question within a chat session."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute(
            """INSERT INTO questions (id, session_id, user_id, chatbot_id, question, question_type,
                                      ai_response, admin_response, source, status, user_email, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, '', ?, ?, ?, ?, ?)""",
            (question_id, session_id, user_id, chatbot_id, question, question_type,
             ai_response, source, status, user_email, now, now)
        )
        # Also touch the parent chat session
        cursor.execute(
            "UPDATE chat_sessions SET updated_at = ? WHERE id = ?",
            (now, session_id)
        )
        conn.commit()
        conn.close()

    def add_widget_inquiry(self, chatbot_id, email, title, description):
        """Record an inquiry submitted through the customer chat widget."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        now = datetime.now().isoformat()

        # 1. Resolve user_id of the owner of this chatbot_id
        cursor.execute("SELECT id FROM users WHERE chatbot_id = ?", (chatbot_id,))
        user_row = cursor.fetchone()
        user_id = user_row[0] if user_row else "user_default"

        # 2. Create a chat session dedicated to this inquiry
        session_id = "cs_" + str(uuid.uuid4())[:12]
        session_title = f"Inquiry: {title[:40]}" if title else f"Inquiry from {email}"
        cursor.execute(
            """INSERT INTO chat_sessions (id, user_id, chatbot_id, title, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (session_id, user_id, chatbot_id, session_title, now, now)
        )

        # 3. Create question/ticket record
        question_id = "q_" + str(uuid.uuid4())[:12]
        formatted_question = f"**{title.strip()}**\n\n{description.strip()}"
        cursor.execute(
            """INSERT INTO questions (id, session_id, user_id, chatbot_id, question, question_type,
                                      ai_response, admin_response, source, status, user_email, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, 'inquiry', '', '', 'Widget Form', 'needs_review', ?, ?, ?)""",
            (question_id, session_id, user_id, chatbot_id, formatted_question, email.strip(), now, now)
        )
        conn.commit()
        conn.close()
        return {
            "question_id": question_id,
            "session_id": session_id
        }

    def update_question_response(self, question_id, ai_response, source="", status="ai_answered"):
        """Update the AI response for a question after generation."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute(
            "UPDATE questions SET ai_response = ?, source = ?, status = ?, updated_at = ? WHERE id = ?",
            (ai_response, source, status, now, question_id)
        )
        conn.commit()
        conn.close()

    def get_session_questions(self, session_id):
        """Get all questions in a chat session, ordered chronologically."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            """SELECT q.id, q.session_id, q.user_id, q.chatbot_id, q.question, q.question_type,
                      q.ai_response, q.admin_response, q.source, q.status, q.created_at, q.updated_at,
                      COALESCE(NULLIF(q.user_email, ''), u.email) as user_email
               FROM questions q
               LEFT JOIN users u ON q.user_id = u.id
               WHERE q.session_id = ?
               ORDER BY q.created_at ASC""",
            (session_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    # --- Admin Dashboard Methods ---

    def get_all_chat_sessions(self, chatbot_id, search="", limit=50, offset=0):
        """Get all chat sessions for admin dashboard with search capability."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if search:
            cursor.execute(
                """SELECT cs.id, cs.user_id, cs.chatbot_id, cs.title, cs.created_at, cs.updated_at,
                          u.email as user_email,
                          (SELECT COUNT(*) FROM questions q WHERE q.session_id = cs.id) as question_count
                   FROM chat_sessions cs
                   LEFT JOIN users u ON cs.user_id = u.id
                   WHERE cs.chatbot_id = ? AND (cs.title LIKE ? OR u.email LIKE ? OR cs.id LIKE ?)
                   ORDER BY cs.updated_at DESC
                   LIMIT ? OFFSET ?""",
                (chatbot_id, f"%{search}%", f"%{search}%", f"%{search}%", limit, offset)
            )
        else:
            cursor.execute(
                """SELECT cs.id, cs.user_id, cs.chatbot_id, cs.title, cs.created_at, cs.updated_at,
                          u.email as user_email,
                          (SELECT COUNT(*) FROM questions q WHERE q.session_id = cs.id) as question_count
                   FROM chat_sessions cs
                   LEFT JOIN users u ON cs.user_id = u.id
                   WHERE cs.chatbot_id = ?
                   ORDER BY cs.updated_at DESC
                   LIMIT ? OFFSET ?""",
                (chatbot_id, limit, offset)
            )
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_all_questions(self, chatbot_id, search="", status_filter="", question_type_filter="", limit=50, offset=0):
        """Get all questions for admin dashboard with filtering and search."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = """SELECT q.id, q.session_id, q.user_id, q.chatbot_id, q.question, q.question_type,
                          q.ai_response, q.admin_response, q.source, q.status, q.created_at, q.updated_at,
                          COALESCE(NULLIF(q.user_email, ''), u.email) as user_email, cs.title as session_title
                   FROM questions q
                   LEFT JOIN users u ON q.user_id = u.id
                   LEFT JOIN chat_sessions cs ON q.session_id = cs.id
                   WHERE q.chatbot_id = ?"""
        params = [chatbot_id]

        if search:
            query += " AND (q.question LIKE ? OR q.ai_response LIKE ? OR COALESCE(NULLIF(q.user_email, ''), u.email) LIKE ? OR q.id LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%", f"%{search}%", f"%{search}%"])

        if status_filter:
            query += " AND q.status = ?"
            params.append(status_filter)

        if question_type_filter:
            query += " AND q.question_type = ?"
            params.append(question_type_filter)

        query += " ORDER BY q.created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_question_by_id(self, question_id):
        """Retrieve a single question by ID with user info."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            """SELECT q.id, q.session_id, q.user_id, q.chatbot_id, q.question, q.question_type,
                      q.ai_response, q.admin_response, q.source, q.status, q.created_at, q.updated_at,
                      COALESCE(NULLIF(q.user_email, ''), u.email) as user_email, cs.title as session_title
               FROM questions q
               LEFT JOIN users u ON q.user_id = u.id
               LEFT JOIN chat_sessions cs ON q.session_id = cs.id
               WHERE q.id = ?""",
            (question_id,)
        )
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def admin_update_question(self, question_id, chatbot_id, status=None, admin_response=None):
        """Admin: Update question status and/or admin response."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        now = datetime.now().isoformat()

        # Verify ownership
        cursor.execute("SELECT 1 FROM questions WHERE id = ? AND chatbot_id = ?", (question_id, chatbot_id))
        if not cursor.fetchone():
            conn.close()
            raise ValueError("Question not found or access denied.")

        updates = ["updated_at = ?"]
        params = [now]

        if status is not None:
            updates.append("status = ?")
            params.append(status)

        if admin_response is not None:
            updates.append("admin_response = ?")
            params.append(admin_response)

        params.append(question_id)
        cursor.execute(f"UPDATE questions SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()
        conn.close()

    def get_dashboard_analytics(self, chatbot_id):
        """Get aggregated analytics for admin dashboard (focused on queries)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Total sessions
        cursor.execute("SELECT COUNT(*) FROM chat_sessions WHERE chatbot_id = ?", (chatbot_id,))
        total_sessions = cursor.fetchone()[0]

        # Queries metrics (question_type = 'inquiry')
        cursor.execute(
            "SELECT COUNT(*) FROM questions WHERE chatbot_id = ? AND question_type = 'inquiry'",
            (chatbot_id,)
        )
        total_queries = cursor.fetchone()[0]

        cursor.execute(
            "SELECT status, COUNT(*) FROM questions WHERE chatbot_id = ? AND question_type = 'inquiry' GROUP BY status",
            (chatbot_id,)
        )
        query_status_counts = {}
        for row in cursor.fetchall():
            query_status_counts[row[0]] = row[1]

        new_queries = query_status_counts.get("new", 0)
        needs_review_queries = query_status_counts.get("needs_review", 0)
        admin_answered_queries = query_status_counts.get("admin_answered", 0)
        resolved_queries = query_status_counts.get("resolved", 0)
        unanswered_queries = new_queries + needs_review_queries

        # Total questions breakdown across all types
        cursor.execute("SELECT COUNT(*) FROM questions WHERE chatbot_id = ?", (chatbot_id,))
        all_questions_count = cursor.fetchone()[0]

        cursor.execute(
            "SELECT question_type, COUNT(*) FROM questions WHERE chatbot_id = ? GROUP BY question_type",
            (chatbot_id,)
        )
        type_counts = {}
        for row in cursor.fetchall():
            type_counts[row[0]] = row[1]

        # Recent activity (queries in last 7 days)
        cursor.execute(
            "SELECT COUNT(*) FROM questions WHERE chatbot_id = ? AND question_type = 'inquiry' AND created_at >= datetime('now', '-7 days')",
            (chatbot_id,)
        )
        recent_queries_7d = cursor.fetchone()[0]

        conn.close()

        return {
            "total_sessions": total_sessions,
            # Queries metrics per requirement: Total Questions, Unanswered, and Needs Review show for queries only
            "total_questions": total_queries,
            "total_queries": total_queries,
            "new_questions": new_queries,
            "unanswered_questions": unanswered_queries,
            "unanswered_queries": unanswered_queries,
            "needs_review": needs_review_queries,
            "needs_review_queries": needs_review_queries,
            "admin_answered": admin_answered_queries,
            "admin_answered_queries": admin_answered_queries,
            "resolved": resolved_queries,
            "resolved_queries": resolved_queries,
            "all_questions_count": all_questions_count,
            "document_questions": type_counts.get("document", 0),
            "general_questions": type_counts.get("general", 0),
            "inquiry_questions": type_counts.get("inquiry", 0),
            "recent_questions_7d": recent_queries_7d
        }

