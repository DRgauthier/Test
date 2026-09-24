import React, { useEffect, useState } from 'react'
import { supabase } from '../lib/supabase'
import { useNavigate } from 'react-router-dom'
import { LogOut, Plus, Play } from 'lucide-react'

export function Lobbies({ user }) {
  const [lobbies, setLobbies] = useState([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    fetchLobbies()

    const subscription = supabase
      .channel('lobbies_changes')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'lobbies' }, fetchLobbies)
      .subscribe()

    return () => {
      supabase.removeChannel(subscription)
    }
  }, [])

  const fetchLobbies = async () => {
    const { data, error } = await supabase
      .from('lobbies')
      .select('*')
      .order('created_at', { ascending: false })

    if (!error) setLobbies(data || [])
    setLoading(false)
  }

  const createLobby = async () => {
    const { data, error } = await supabase
      .from('lobbies')
      .insert([{ host_id: user.id }])
      .select()

    if (!error && data) {
      navigate(`/game/${data[0].id}`)
    }
  }

  const joinLobby = async (lobbyId) => {
    const { error } = await supabase
      .from('lobbies')
      .update({ guest_id: user.id, status: 'playing' })
      .eq('id', lobbyId)
      .is('guest_id', null)

    if (!error) {
      navigate(`/game/${lobbyId}`)
    } else {
      // Might already be joined or full
      navigate(`/game/${lobbyId}`)
    }
  }

  const handleLogout = async () => {
    await supabase.auth.signOut()
    navigate('/login')
  }

  const getDisplayName = (email) => {
    if (!email) return 'User'
    return email.substring(0, 3).toUpperCase()
  }

  return (
    <div className="max-w-4xl mx-auto p-4">
      <div className="flex justify-between items-center mb-8 bg-white p-4 rounded shadow">
        <h1 className="text-2xl font-bold">Lobbies</h1>
        <div className="flex items-center gap-4">
          <span className="font-medium text-gray-700">
            Welcome, {getDisplayName(user.email)}
          </span>
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 bg-gray-200 px-3 py-1 rounded hover:bg-gray-300"
          >
            <LogOut size={16} /> Logout
          </button>
        </div>
      </div>

      <div className="mb-6">
        <button
          onClick={createLobby}
          className="flex items-center gap-2 bg-blue-500 text-white px-4 py-2 rounded shadow hover:bg-blue-600"
        >
          <Plus size={20} /> Create New Game
        </button>
      </div>

      <div className="bg-white rounded shadow overflow-hidden">
        {loading ? (
          <p className="p-4 text-center text-gray-500">Loading lobbies...</p>
        ) : lobbies.length === 0 ? (
          <p className="p-4 text-center text-gray-500">No active lobbies. Create one!</p>
        ) : (
          <ul className="divide-y divide-gray-200">
            {lobbies.map(lobby => (
              <li key={lobby.id} className="p-4 flex justify-between items-center hover:bg-gray-50">
                <div>
                  <p className="font-medium">Game {lobby.id.substring(0, 8)}</p>
                  <p className="text-sm text-gray-500">Status: {lobby.status}</p>
                </div>
                {lobby.status !== 'finished' && (
                  <button
                    onClick={() => joinLobby(lobby.id)}
                    className="flex items-center gap-2 bg-green-500 text-white px-4 py-2 rounded hover:bg-green-600"
                  >
                    <Play size={16} /> {lobby.host_id === user.id || lobby.guest_id === user.id ? 'Rejoin' : 'Join'}
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
