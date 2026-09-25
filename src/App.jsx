import React, { useEffect, useState } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { supabase } from './lib/supabase'
import { Login } from './pages/Login'
import { Lobbies } from './pages/Lobbies'
import { Game } from './pages/Game'
import { LobbyReady } from './pages/LobbyReady'

function App() {
  const [session, setSession] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session)
      setLoading(false)
    })

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session)
    })

    return () => subscription.unsubscribe()
  }, [])

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center">Loading...</div>
  }

  return (
    <div className="min-h-screen bg-gray-100">
      <Routes>
        <Route
          path="/login"
          element={!session ? <Login /> : <Navigate to="/" />}
        />
        <Route
          path="/"
          element={session ? <Lobbies user={session.user} /> : <Navigate to="/login" />}
        />
        <Route
          path="/lobby/:id"
          element={session ? <LobbyReady user={session.user} /> : <Navigate to="/login" />}
        />
        <Route
          path="/game/:id"
          element={session ? <Game user={session.user} /> : <Navigate to="/login" />}
        />
      </Routes>
    </div>
  )
}

export default App
