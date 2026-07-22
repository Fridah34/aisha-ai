import { useEffect, useState } from 'react'
import { useWebSocket } from '../context/WebSocketContext'

export default function WebSocketTest() {
  const { isConnected, connectionError, lastMessage, sendMessage } = useWebSocket()
  const [testMessage, setTestMessage] = useState('')

  return (
    <div className="p-4 bg-white border border-slate-200 rounded-lg max-w-md">
      <h3 className="font-medium mb-2">WebSocket Test</h3>
      
      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <span className={`w-3 h-3 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
          <span className="text-sm">
            {isConnected ? 'Connected' : 'Disconnected'}
          </span>
          {connectionError && (
            <span className="text-xs text-red-500 ml-2">{connectionError}</span>
          )}
        </div>
        
        {lastMessage && (
          <div className="text-xs bg-slate-50 p-2 rounded">
            <p className="font-medium text-slate-600">Last message:</p>
            <pre className="mt-1 text-slate-700 overflow-x-auto">
              {JSON.stringify(lastMessage, null, 2)}
            </pre>
          </div>
        )}
        
        <div className="flex gap-2">
          <input
            type="text"
            value={testMessage}
            onChange={(e) => setTestMessage(e.target.value)}
            placeholder="Test message"
            className="flex-1 px-3 py-1 border border-slate-200 rounded text-sm"
          />
          <button
            onClick={() => {
              if (testMessage) {
                sendMessage({ type: 'test', message: testMessage })
                setTestMessage('')
              }
            }}
            disabled={!isConnected}
            className="px-3 py-1 bg-amber-500 text-white rounded text-sm disabled:opacity-50"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  )
}