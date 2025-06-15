import { useState } from 'react'
import './App.css'

interface Message {
  text: string;
  isUser: boolean;
  timestamp: Date;
}

function App() {
  const [messages, setMessages] = useState<Message[]>([])
  const [inputText, setInputText] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!inputText.trim()) return

    const userMessage: Message = {
      text: inputText,
      isUser: true,
      timestamp: new Date()
    }
    setMessages(prev => [...prev, userMessage])
    setInputText('')
    setIsLoading(true)

    try {
      const response = await fetch('http://0.0.0.0:9001/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: inputText }),
      })

      const data = await response.json()
      
      const botMessage: Message = {
        text: data.response,
        isUser: false,
        timestamp: new Date()
      }
      setMessages(prev => [...prev, botMessage])
    } catch (error) {
      console.error('Error:', error)
      const errorMessage: Message = {
        text: 'Sorry, I encountered an error. Please try again.',
        isUser: false,
        timestamp: new Date()
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="app">
      <header className="hero">
        <div className="hero-content">
          <h1>Welcome to HQ</h1>
        </div>
      </header>

      <main className="chat-container">
        <div className="messages-container">
          {messages.length === 0 ? (
            <div className="welcome-message">
              <h2>How can I help you today?</h2>
              <p>I'm your AI assistant, ready to assist with any task.</p>
            </div>
          ) : (
            messages.map((message, index) => (
              <div
                key={index}
                className={`message ${message.isUser ? 'user-message' : 'bot-message'}`}
              >
                <div className="message-content">
                  <div className="message-text">{message.text}</div>
                  <div className="message-timestamp">
                    {message.timestamp.toLocaleTimeString()}
                  </div>
                </div>
              </div>
            ))
          )}
          {isLoading && (
            <div className="message bot-message">
              <div className="message-content">
                <div className="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </div>
          )}
        </div>

        <form onSubmit={handleSubmit} className="input-container">
          <input
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            placeholder="Type your message..."
            className="message-input"
          />
          <button
            type="submit"
            className="send-button"
            disabled={isLoading || !inputText.trim()}
          >
            Send
          </button>
        </form>
      </main>
    </div>
  )
}

export default App
 