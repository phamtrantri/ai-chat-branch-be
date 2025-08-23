ALTER TABLE conversations ADD message_id INTEGER REFERENCES conversations(id) ON DELETE CASCADE;
CREATE INDEX idx_conversations_message_id ON conversations(message_id);