import { useState, useRef, useEffect } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Send, Bot, User, Loader2 } from 'lucide-react'
import api from '../api/client'

interface Message {
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

interface StoredMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp: string
}

const STORAGE_KEY = 'agent_chat_state'

function loadChatState(): { messages: Message[], threadId: string | null } {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored) {
      const parsed = JSON.parse(stored)
      return {
        messages: parsed.messages.map((m: StoredMessage) => ({
          ...m,
          timestamp: new Date(m.timestamp)
        })),
        threadId: parsed.threadId
      }
    }
  } catch (e) {
    console.error('Failed to load chat state:', e)
  }
  return { messages: [], threadId: null }
}

function saveChatState(messages: Message[], threadId: string | null) {
  try {
    const toStore = {
      messages: messages.map(m => ({
        ...m,
        timestamp: m.timestamp.toISOString()
      })),
      threadId
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(toStore))
  } catch (e) {
    console.error('Failed to save chat state:', e)
  }
}

export default function Chat() {
  const initialState = loadChatState()
  const [messages, setMessages] = useState<Message[]>(initialState.messages)
  const [input, setInput] = useState('')
  const [threadId, setThreadId] = useState<string | null>(initialState.threadId)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  // Save chat state whenever messages or threadId changes
  useEffect(() => {
    saveChatState(messages, threadId)
  }, [messages, threadId])

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const sendMessage = useMutation({
    mutationFn: async (message: string) => {
      const response = await api.post('/api/v1/chat', {
        message,
        thread_id: threadId,
      })
      return response.data
    },
    onSuccess: (data) => {
      setThreadId(data.thread_id)
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: data.response,
          timestamp: new Date(),
        },
      ])
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || sendMessage.isPending) return

    const userMessage = input.trim()
    setInput('')

    setMessages((prev) => [
      ...prev,
      {
        role: 'user',
        content: userMessage,
        timestamp: new Date(),
      },
    ])

    sendMessage.mutate(userMessage)
  }

  const handleNewChat = () => {
    setMessages([])
    setThreadId(null)
    localStorage.removeItem(STORAGE_KEY)
  }

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)]">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold text-gray-900">Chat with Agent</h1>
        <button
          onClick={handleNewChat}
          className="px-4 py-2 text-sm bg-gray-200 hover:bg-gray-300 rounded-lg transition-colors"
        >
          New Chat
        </button>
      </div>

      {/* Messages Container */}
      <div className="flex-1 bg-white rounded-xl shadow-sm overflow-hidden flex flex-col">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.length === 0 ? (
            <div className="text-center text-gray-500 py-12">
              <Bot className="w-12 h-12 mx-auto mb-4 text-gray-400" />
              <p className="text-lg font-medium">Start a conversation</p>
              <p className="mt-2">Ask about contracts, HR operations, or anything else!</p>
              <div className="mt-6 flex flex-wrap gap-2 justify-center">
                {[
                  'Show expiring contracts',
                  'List employees',
                  'Pending leave requests',
                  'Contract summary',
                ].map((suggestion) => (
                  <button
                    key={suggestion}
                    onClick={() => setInput(suggestion)}
                    className="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded-full text-sm transition-colors"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((message, index) => (
              <div
                key={index}
                className={`flex gap-3 ${
                  message.role === 'user' ? 'justify-end' : 'justify-start'
                }`}
              >
                {message.role === 'assistant' && (
                  <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center flex-shrink-0">
                    <Bot className="w-5 h-5 text-blue-600" />
                  </div>
                )}
                <div
                  className={`max-w-[70%] rounded-2xl px-4 py-3 ${
                    message.role === 'user'
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-900'
                  }`}
                >
                  <p className="whitespace-pre-wrap">{message.content}</p>
                  <p className={`text-xs mt-1 ${
                    message.role === 'user' ? 'text-blue-200' : 'text-gray-500'
                  }`}>
                    {message.timestamp.toLocaleTimeString()}
                  </p>
                </div>
                {message.role === 'user' && (
                  <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center flex-shrink-0">
                    <User className="w-5 h-5 text-white" />
                  </div>
                )}
              </div>
            ))
          )}
          {sendMessage.isPending && (
            <div className="flex gap-3">
              <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                <Bot className="w-5 h-5 text-blue-600" />
              </div>
              <div className="bg-gray-100 rounded-2xl px-4 py-3">
                <Loader2 className="w-5 h-5 animate-spin text-gray-500" />
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <form onSubmit={handleSubmit} className="p-4 border-t">
          <div className="flex gap-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type your message..."
              className="flex-1 px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              disabled={sendMessage.isPending}
            />
            <button
              type="submit"
              disabled={!input.trim() || sendMessage.isPending}
              className="px-6 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <Send className="w-5 h-5" />
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
