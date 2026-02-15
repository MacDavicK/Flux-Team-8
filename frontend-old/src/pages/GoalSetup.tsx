import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import type { ChatMessage } from '../types';
import styles from './GoalSetup.module.css';

const initialMessage: ChatMessage = {
  id: '1',
  role: 'assistant',
  content: 'What goal would you like to work on?',
  timestamp: new Date().toISOString(),
};

function GoalSetup() {
  const navigate = useNavigate();
  const [messages, setMessages] = useState<ChatMessage[]>([initialMessage]);
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: trimmed,
      timestamp: new Date().toISOString(),
    };

    console.log('User message:', trimmed);
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <section className={styles.container}>
      <header className={styles.chatHeader}>
        <button
          className={styles.backButton}
          onClick={() => navigate('/dashboard')}
          aria-label="Go back to dashboard"
        >
          &larr;
        </button>
        <h2 className={styles.heading}>Goal Setup</h2>
      </header>

      <div className={styles.messageList}>
        {messages.map((msg) => (
          <article
            key={msg.id}
            className={`${styles.message} ${msg.role === 'user' ? styles.user : styles.assistant}`}
          >
            <p className={styles.messageContent}>{msg.content}</p>
          </article>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <div className={styles.inputBar}>
        <input
          type="text"
          className={styles.input}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type your goal..."
          aria-label="Type your goal"
        />
        <button
          className={styles.sendButton}
          onClick={handleSend}
          disabled={!input.trim()}
          aria-label="Send message"
        >
          Send
        </button>
      </div>
    </section>
  );
}

export default GoalSetup;
