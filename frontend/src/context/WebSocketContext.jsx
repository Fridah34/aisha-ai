// src/context/WebSocketContext.jsx
import { createContext, useContext, useEffect, useState, useRef, useCallback } from 'react'
import { USER_ID } from '../api/client'

const WebSocketContext = createContext()

export function WebSocketProvider({ children }) {
  const [isConnected, setIsConnected] = useState(false)
  const [lastMessage, setLastMessage] = useState(null)
  const [connectionError, setConnectionError] = useState(null)
  const wsRef = useRef(null)
  const reconnectTimeoutRef = useRef(null)
  const reconnectAttempts = useRef(0)
  const MAX_RECONNECT_ATTEMPTS = 5

  const connect = useCallback(() => {
    // Close existing connection if any
    if (wsRef.current) {
      try {
        wsRef.current.close()
      } catch (e) {
        // Ignore
      }
      wsRef.current = null
    }

    try {
      // Use the same host as your API
      const wsUrl = `ws://127.0.0.1:8000/ws/conversations/${USER_ID}`
      console.log(`🔌 Attempting WebSocket connection to: ${wsUrl}`)
      
      const ws = new WebSocket(wsUrl)
      
      ws.onopen = () => {
        console.log('✅ WebSocket connected successfully')
        setIsConnected(true)
        setConnectionError(null)
        reconnectAttempts.current = 0
        // Send initial ping
        try {
          ws.send(JSON.stringify({ type: 'ping' }))
        } catch (e) {
          console.warn('Could not send initial ping:', e)
        }
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          console.log('📨 WebSocket message received:', data)
          setLastMessage(data)
          
          // Handle different message types
          if (data.type === 'status_change') {
            window.dispatchEvent(new CustomEvent('conversation_status_change', {
              detail: {
                customerId: data.customer_id,
                newStatus: data.new_status
              }
            }))
          } else if (data.type === 'new_message') {
            window.dispatchEvent(new CustomEvent('new_conversation_message', {
              detail: {
                customerId: data.customer_id,
                message: data.message,
                sender: data.sender,
                timestamp: data.timestamp
              }
            }))
          } else if (data.type === 'connection_established') {
            console.log('✅ Connection confirmed by server:', data.message)
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error, event.data)
        }
      }

      ws.onclose = (event) => {
        console.log(`🔌 WebSocket disconnected. Code: ${event.code}, Reason: ${event.reason}`)
        setIsConnected(false)
        wsRef.current = null
        
        // Don't reconnect if it was a normal closure
        if (event.code === 1000 || event.code === 1001) {
          console.log('Normal closure, not reconnecting')
          return
        }
        
        // Attempt reconnection
        if (reconnectAttempts.current < MAX_RECONNECT_ATTEMPTS) {
          reconnectAttempts.current += 1
          const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000)
          console.log(`🔄 Reconnecting in ${delay}ms... (Attempt ${reconnectAttempts.current}/${MAX_RECONNECT_ATTEMPTS})`)
          
          if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current)
          }
          reconnectTimeoutRef.current = setTimeout(connect, delay)
        } else {
          console.error('❌ Max reconnection attempts reached')
          setConnectionError('Failed to connect after multiple attempts')
        }
      }

      ws.onerror = (error) => {
        console.error('❌ WebSocket error:', error)
        setConnectionError('WebSocket connection error')
        // The onclose handler will handle reconnection
      }

      wsRef.current = ws
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error)
      setConnectionError(error.message)
      
      // Attempt reconnection
      if (reconnectAttempts.current < MAX_RECONNECT_ATTEMPTS) {
        reconnectAttempts.current += 1
        const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000)
        console.log(`🔄 Reconnecting in ${delay}ms... (Attempt ${reconnectAttempts.current})`)
        
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current)
        }
        reconnectTimeoutRef.current = setTimeout(connect, delay)
      }
    }
  }, [])

  // Send a message through WebSocket
  const sendMessage = useCallback((message) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      try {
        wsRef.current.send(JSON.stringify(message))
        return true
      } catch (error) {
        console.error('Failed to send message:', error)
        return false
      }
    }
    console.warn('WebSocket not connected, message not sent')
    return false
  }, [])

  // Ping the server periodically to keep connection alive
  useEffect(() => {
    const pingInterval = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        try {
          wsRef.current.send(JSON.stringify({ type: 'ping' }))
        } catch (e) {
          // Ignore
        }
      }
    }, 30000) // Every 30 seconds

    return () => clearInterval(pingInterval)
  }, [])

  // Connect on mount
  useEffect(() => {
    connect()
    
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      if (wsRef.current) {
        try {
          wsRef.current.close(1000, 'Component unmounting')
        } catch (e) {
          // Ignore
        }
      }
    }
  }, [connect])

  const value = {
    isConnected,
    lastMessage,
    connectionError,
    sendMessage,
    reconnect: connect
  }

  return (
    <WebSocketContext.Provider value={value}>
      {children}
    </WebSocketContext.Provider>
  )
}

export function useWebSocket() {
  const context = useContext(WebSocketContext)
  if (!context) {
    throw new Error('useWebSocket must be used within a WebSocketProvider')
  }
  return context
}