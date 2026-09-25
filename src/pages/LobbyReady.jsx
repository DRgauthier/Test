import React, { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { supabase } from '../lib/supabase'
import { BOARD_SIZE, createTileBag, drawTiles } from '../lib/gameLogic'

export function LobbyReady({ user }) {
  const { id } = useParams()
  const navigate = useNavigate()

  const [lobby, setLobby] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchLobbyAndInitialize()

    const subscription = supabase
      .channel(`lobby_ready_${id}`)
      .on('postgres_changes', { event: 'UPDATE', schema: 'public', table: 'lobbies', filter: `id=eq.${id}` }, (payload) => {
        setLobby(payload.new)
      })
      .subscribe()

    return () => {
      supabase.removeChannel(subscription)
    }
  }, [id])

  const fetchLobbyAndInitialize = async () => {
    const { data, error } = await supabase
      .from('lobbies')
      .select('*')
      .eq('id', id)
      .single()

    if (error || !data) {
      navigate('/')
      return
    }

    // If game state is empty and we are the host, initialize it
    if (Object.keys(data.game_state).length === 0 && data.host_id === user.id) {
      await initializeGame(data)
    } else {
      setLobby(data)
      setLoading(false)
    }
  }

  const initializeGame = async (lobbyData) => {
    const bag = createTileBag()
    const hostTiles = drawTiles(bag, 7)
    const guestTiles = lobbyData.guest_id ? drawTiles(bag, 7) : []

    const initialState = {
      board: Array(BOARD_SIZE).fill(null).map(() => Array(BOARD_SIZE).fill(null)),
      bag,
      players: {
        [lobbyData.host_id]: { score: 0, rack: hostTiles },
        ...(lobbyData.guest_id ? { [lobbyData.guest_id]: { score: 0, rack: guestTiles } } : {})
      },
      turn: lobbyData.host_id,
      history: []
    }

    const { data, error } = await supabase
      .from('lobbies')
      .update({ game_state: initialState })
      .eq('id', id)
      .select()
      .single()

    if (!error && data) {
      setLobby(data)
    }
    setLoading(false)
  }

  const isGameReady = lobby && lobby.game_state && lobby.game_state.board && lobby.game_state.players;

  return (
    <div className="min-h-screen bg-stone-100 p-8 flex flex-col items-center justify-center">
      <div className="bg-white p-8 rounded shadow-lg max-w-md w-full text-center">
        <h1 className="text-2xl font-bold mb-6">Game Lobby</h1>

        {loading || !isGameReady ? (
          <div>
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
            <p className="text-gray-600">Preparing game board...</p>
          </div>
        ) : (
          <div>
            <p className="text-green-600 font-medium mb-6">The game is ready!</p>
            <button
              onClick={() => navigate(`/game/${id}`)}
              className="w-full bg-blue-500 text-white px-6 py-3 rounded shadow hover:bg-blue-600 font-bold text-lg"
            >
              Enter Game
            </button>
          </div>
        )}

        <button
          onClick={() => navigate('/')}
          className="mt-6 text-gray-500 hover:text-gray-700 text-sm"
        >
          Cancel and return to Main Menu
        </button>
      </div>
    </div>
  )
}
