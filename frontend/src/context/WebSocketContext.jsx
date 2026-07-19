// src/context/WebSocketContext.jsx
import { createContext, useContext, useEffect, useState, useRef, useCallback } from 'react'
import { getWebSocketUrl } from '../api/client'
import { useAuth } from '../hooks/useAuth'

const WebSocketContext = createContext()

export function WebSocketProvider({ children }) {
  const { user, isAuthenticated } = useAuth()
  const [isConnected, setIsConnected] = useState(false)
  const [lastMessage, setLastMessage] = useState(null)
  const [connectionError, setConnectionError] = useState(null)
  const wsRef = useRef(null)
  const reconnectTimeoutRef = useRef(null)
  const reconnectAttempts = useRef(0)
  const MAX_RECONNECT_ATTEMPTS = 5

  const connect = useCallback(() => {
    if(!isAuthenticated || !user?.id ) {
      console.warn('WebSocket: no authenticated user yet, skipping connect')
      return
    }
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
      const wsUrl = `${getWebSocketUrl()}/${user.id}`
      console.log(` Attempting WebSocket connection to: ${wsUrl}`)
      
      const ws = new WebSocket(wsUrl)
      
      ws.onopen = () => {
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
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error)
        }
      }

      ws.onclose = (event) => {
        setIsConnected(false)
        wsRef.current = null
        
        // Don't reconnect if it was a normal closure
        if (event.code === 1000 || event.code === 1001) {
          return
        }
        
        // Attempt reconnection
        if (reconnectAttempts.current < MAX_RECONNECT_ATTEMPTS) {
          reconnectAttempts.current += 1
          const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000)
          
          if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current)
          }
          reconnectTimeoutRef.current = setTimeout(connect, delay)
        } else {
          setConnectionError('Failed to connect after multiple attempts')
        }
      }

      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        setConnectionError('WebSocket connection error')
        // The onclose handler will handle reconnection
      }

      wsRef.current = ws
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error)
      setConnectionError(error.message)
      
      // Attempt reconnectionssss
      if (reconnectAttempts.current < MAX_RECONNECT_ATTEMPTS) {
        reconnectAttempts.current += 1
        const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000)
        console.log(` Reconnecting in ${delay}ms... (Attempt ${reconnectAttempts.current})`)
        
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current)
        }
        reconnectTimeoutRef.current = setTimeout(connect, delay)
      }
    }
  }, [ isAuthenticated, user?.id])

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
    if (isAuthenticated && user?.id) {
      connect()
    } else {
      if (wsRef.current) {
        try {
          wsRef.current.close(1000, 'User logged out')
        } catch (e) {
          // Ignore
        }
        wsRef.current = null
      }
      setIsConnected(false)
    }
    
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
  }, [connect, isAuthenticated, user?.id])

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