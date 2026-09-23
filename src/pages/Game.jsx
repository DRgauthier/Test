import React, { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { supabase } from '../lib/supabase'
import { BOARD_SIZE, BOARD_LAYOUT, MULTIPLIERS, createTileBag, drawTiles } from '../lib/gameLogic'
import { isValidWord, getTileValue } from '../lib/wordValidation'
import { validateAndScoreMove } from '../lib/scoring'
import { ArrowLeft, RefreshCw, Check } from 'lucide-react'

export function Game({ user }) {
  const { id } = useParams()
  const navigate = useNavigate()

  const [lobby, setLobby] = useState(null)
  const [gameState, setGameState] = useState(null)
  const [isHost, setIsHost] = useState(false)
  const [loading, setLoading] = useState(true)

  // Local state for current turn
  const [selectedTile, setSelectedTile] = useState(null) // index in rack
  const [placedTiles, setPlacedTiles] = useState([]) // [{row, col, letter, rackIndex}]

  useEffect(() => {
    fetchLobbyAndGame()

    const subscription = supabase
      .channel(`game_${id}`)
      .on('postgres_changes', { event: 'UPDATE', schema: 'public', table: 'lobbies', filter: `id=eq.${id}` }, (payload) => {
        setLobby(payload.new)
        setGameState(payload.new.game_state)
        // Clear local placed tiles if state changes from remote
        setPlacedTiles([])
      })
      .subscribe()

    return () => {
      supabase.removeChannel(subscription)
    }
  }, [id])

  const fetchLobbyAndGame = async () => {
    const { data, error } = await supabase
      .from('lobbies')
      .select('*')
      .eq('id', id)
      .single()

    if (error || !data) {
      navigate('/')
      return
    }

    setLobby(data)
    setIsHost(data.host_id === user.id)

    // Initialize game state if empty and we are host
    if (Object.keys(data.game_state).length === 0 && data.host_id === user.id) {
      initializeGame(data)
    } else {
      setGameState(data.game_state)
    }

    setLoading(false)
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

    await supabase
      .from('lobbies')
      .update({ game_state: initialState })
      .eq('id', id)
  }

  // Effect to draw initial tiles for guest when they join
  useEffect(() => {
    if (isHost && lobby && lobby.guest_id && gameState && !gameState.players[lobby.guest_id]) {
      const bag = [...gameState.bag]
      const guestTiles = drawTiles(bag, 7)

      const newState = {
        ...gameState,
        bag,
        players: {
          ...gameState.players,
          [lobby.guest_id]: { score: 0, rack: guestTiles }
        }
      }

      updateGameState(newState)
    }
  }, [lobby, gameState, isHost])

  const updateGameState = async (newState) => {
    await supabase
      .from('lobbies')
      .update({ game_state: newState })
      .eq('id', id)
  }

  const handleCellClick = (row, col) => {
    if (!isMyTurn) return;

    // Prevent host from playing if guest hasn't joined (which causes nextTurn to be null and softlocks)
    if (!lobby.guest_id) {
      alert("Please wait for a guest to join before playing.");
      return;
    }

    // Check if there's already a placed tile here in current turn
    const existingPlacementIndex = placedTiles.findIndex(pt => pt.row === row && pt.col === col);

    if (existingPlacementIndex !== -1) {
      // Pick it back up
      const placement = placedTiles[existingPlacementIndex];
      setPlacedTiles(placedTiles.filter((_, i) => i !== existingPlacementIndex));
      setSelectedTile(placement.rackIndex);
      return;
    }

    // Must not be an already finalized tile on board
    if (gameState.board[row][col] !== null) return;

    // Place tile
    if (selectedTile !== null) {
      let letter = myRack[selectedTile];
      if (letter === null) return; // Already placed

      if (letter === '_') {
        const choice = prompt("Enter the letter this blank tile represents:");
        if (!choice || choice.length !== 1 || !/[a-zA-Z]/.test(choice)) {
          alert("Invalid letter.");
          return;
        }
        // Store as lowercase to identify it as a blank in scoring
        letter = choice.toLowerCase();
      }

      setPlacedTiles([...placedTiles, { row, col, letter, rackIndex: selectedTile }]);
      setSelectedTile(null);
    }
  }

  const handleRackClick = (index) => {
    if (!isMyTurn) return;
    if (myRack[index] === null) return; // Tile is placed on board
    setSelectedTile(selectedTile === index ? null : index);
  }

  const handleRecall = () => {
    setPlacedTiles([]);
    setSelectedTile(null);
  }

  const handleSubmitTurn = async () => {
    if (!isMyTurn || placedTiles.length === 0) return;

    const validationResult = validateAndScoreMove(gameState.board, placedTiles);

    if (!validationResult.valid) {
      alert(validationResult.error);
      return;
    }

    let newBoard = gameState.board.map(row => [...row]);
    placedTiles.forEach(pt => {
      newBoard[pt.row][pt.col] = pt.letter;
    });

    let newBag = [...gameState.bag];
    let newRack = [...myRack];

    // Remove placed from rack
    placedTiles.forEach(pt => {
      newRack[pt.rackIndex] = null;
    });
    newRack = newRack.filter(l => l !== null);

    // Replenish
    const drawn = drawTiles(newBag, 7 - newRack.length);
    newRack = [...newRack, ...drawn];

    const nextTurn = lobby.host_id === user.id ? lobby.guest_id : lobby.host_id;

    const currentScore = gameState.players[user.id].score + validationResult.score;

    const newState = {
      ...gameState,
      board: newBoard,
      bag: newBag,
      players: {
        ...gameState.players,
        [user.id]: { score: currentScore, rack: newRack }
      },
      turn: nextTurn
    };

    setPlacedTiles([]);
    setSelectedTile(null);
    await updateGameState(newState);
  }

  const handlePass = async () => {
    if (!isMyTurn) return;
    if (!lobby.guest_id) {
      alert("Please wait for a guest to join.");
      return;
    }
    if (placedTiles.length > 0) {
      alert("Recall your tiles before passing.");
      return;
    }

    const nextTurn = lobby.host_id === user.id ? lobby.guest_id : lobby.host_id;
    const newState = {
      ...gameState,
      turn: nextTurn
    };

    setPlacedTiles([]);
    setSelectedTile(null);
    await updateGameState(newState);
  }

  const handleSwap = async () => {
    if (!isMyTurn) return;
    if (!lobby.guest_id) {
      alert("Please wait for a guest to join.");
      return;
    }
    if (placedTiles.length > 0) {
      alert("Recall your tiles before swapping.");
      return;
    }

    // A simple implementation: swap selected tile, or all tiles if none selected
    let tilesToSwapIndices = [];
    if (selectedTile !== null) {
      tilesToSwapIndices = [selectedTile];
    } else {
      const confirmSwapAll = confirm("No tile selected. Do you want to swap all your tiles?");
      if (!confirmSwapAll) return;
      tilesToSwapIndices = myRack.map((_, i) => i);
    }

    if (gameState.bag.length < tilesToSwapIndices.length) {
      alert("Not enough tiles in bag to swap.");
      return;
    }

    let newBag = [...gameState.bag];
    let newRack = [...myRack];

    let returnedTiles = [];
    tilesToSwapIndices.forEach(idx => {
      returnedTiles.push(newRack[idx]);
      newRack[idx] = null;
    });
    newRack = newRack.filter(l => l !== null);

    // Mix returned tiles back into the bag (shuffle simple approach: push and sort random)
    newBag = [...newBag, ...returnedTiles];
    newBag.sort(() => Math.random() - 0.5);

    const drawn = drawTiles(newBag, tilesToSwapIndices.length);
    newRack = [...newRack, ...drawn];

    const nextTurn = lobby.host_id === user.id ? lobby.guest_id : lobby.host_id;
    const newState = {
      ...gameState,
      bag: newBag,
      players: {
        ...gameState.players,
        [user.id]: { score: gameState.players[user.id].score, rack: newRack }
      },
      turn: nextTurn
    };

    setPlacedTiles([]);
    setSelectedTile(null);
    await updateGameState(newState);
  }


  if (loading || !gameState) {
    return <div className="p-8 text-center">Loading game...</div>
  }

  const isMyTurn = gameState.turn === user.id;
  const myPlayerState = gameState.players[user.id];
  const myRack = myPlayerState ? [...myPlayerState.rack] : [];

  // Blank out tiles in rack that are currently placed on the board locally
  placedTiles.forEach(pt => {
    myRack[pt.rackIndex] = null;
  });

  const getMultiplierColor = (type) => {
    switch(type) {
      case MULTIPLIERS.TW: return 'bg-red-400';
      case MULTIPLIERS.DW: return 'bg-pink-300';
      case MULTIPLIERS.TL: return 'bg-blue-400';
      case MULTIPLIERS.DL: return 'bg-blue-200';
      default: return 'bg-stone-200';
    }
  }

  const getMultiplierText = (type) => {
    switch(type) {
      case MULTIPLIERS.TW: return 'TW';
      case MULTIPLIERS.DW: return 'DW';
      case MULTIPLIERS.TL: return 'TL';
      case MULTIPLIERS.DL: return 'DL';
      default: return '';
    }
  }

  const getDisplayName = (email) => {
    if (!email) return 'User'
    return email.substring(0, 3).toUpperCase()
  }

  // Determine emails to display if possible (since we don't have them in game_state, we can just use ID substrings or "Host/Guest" if email isn't readily available without another join, but user requested 3 letters. Assuming we can't easily fetch guest email synchronously here without modifying schema, we'll just show 'Host' / 'Guest' if we don't have it, but for 'You' we can show it)

  return (
    <div className="min-h-screen bg-stone-100 p-4">
      <div className="max-w-6xl mx-auto flex flex-col md:flex-row gap-8">

        {/* Left Column - Board */}
        <div className="flex-1">
          <div className="mb-4 flex justify-between items-center bg-white p-4 rounded shadow">
            <button
              onClick={() => navigate('/')}
              className="flex items-center gap-2 text-gray-600 hover:text-gray-900"
            >
              <ArrowLeft size={20} /> Leave
            </button>
            <div className="font-bold text-lg">
              {isMyTurn ? <span className="text-green-600">Your Turn</span> : <span className="text-gray-500">Opponent's Turn</span>}
            </div>
          </div>

          <div className="bg-white p-2 rounded shadow inline-block">
            <div className="grid grid-cols-15 gap-1 border-2 border-stone-800 bg-stone-800 p-1" style={{gridTemplateColumns: `repeat(${BOARD_SIZE}, minmax(0, 1fr))`}}>
              {gameState.board.map((row, rIndex) => (
                row.map((cell, cIndex) => {
                  const multiplier = BOARD_LAYOUT[rIndex][cIndex];
                  const localPlacement = placedTiles.find(pt => pt.row === rIndex && pt.col === cIndex);
                  const displayLetter = cell || (localPlacement ? localPlacement.letter : null);
                  const isLocallyPlaced = !!localPlacement;

                  return (
                    <div
                      key={`${rIndex}-${cIndex}`}
                      className={`w-8 h-8 md:w-10 md:h-10 flex items-center justify-center relative font-bold text-lg cursor-pointer
                        ${displayLetter ? 'bg-amber-100 border-2 border-amber-300' : getMultiplierColor(multiplier)}
                        ${isLocallyPlaced ? 'ring-2 ring-blue-500' : ''}
                      `}
                      onClick={() => handleCellClick(rIndex, cIndex)}
                    >
                      {!displayLetter && multiplier && (
                        <span className="text-[10px] text-stone-700 opacity-70 font-sans">{getMultiplierText(multiplier)}</span>
                      )}
                      {displayLetter && (
                        <>
                          <span>{displayLetter.toUpperCase()}</span>
                          <span className="absolute bottom-0.5 right-0.5 text-[8px] text-stone-600">{getTileValue(displayLetter)}</span>
                        </>
                      )}
                    </div>
                  )
                })
              ))}
            </div>
          </div>
        </div>

        {/* Right Column - Player Info & Controls */}
        <div className="w-full md:w-80 flex flex-col gap-4">

          <div className="bg-white p-4 rounded shadow">
            <h3 className="font-bold text-lg mb-4 border-b pb-2">Scores</h3>
            <div className="flex justify-between mb-2">
              <span className={lobby.host_id === user.id ? 'font-bold text-blue-600' : ''}>
                {lobby.host_id === user.id ? getDisplayName(user.email) : 'Host'}
              </span>
              <span className="font-mono font-bold">{gameState.players[lobby.host_id]?.score || 0}</span>
            </div>
            <div className="flex justify-between">
              <span className={lobby.guest_id === user.id ? 'font-bold text-blue-600' : ''}>
                {lobby.guest_id ? (lobby.guest_id === user.id ? getDisplayName(user.email) : 'Guest') : 'Waiting...'}
              </span>
              <span className="font-mono font-bold">{lobby.guest_id ? (gameState.players[lobby.guest_id]?.score || 0) : '-'}</span>
            </div>
            <div className="mt-4 pt-2 border-t text-sm text-gray-500 text-center">
              Tiles remaining: {gameState.bag.length}
            </div>
          </div>

          <div className="bg-white p-4 rounded shadow">
            <h3 className="font-bold text-lg mb-4 border-b pb-2">Your Tiles</h3>
            {myPlayerState ? (
              <div className="flex gap-2 justify-center mb-6 h-12">
                {myRack.map((letter, i) => (
                  <div
                    key={i}
                    onClick={() => handleRackClick(i)}
                    className={`w-10 h-12 flex items-center justify-center relative font-bold text-xl cursor-pointer border-2 rounded shadow-sm
                      ${letter === null ? 'opacity-0' : 'bg-amber-100'}
                      ${selectedTile === i ? 'border-blue-500 ring-2 ring-blue-200 -translate-y-2' : 'border-amber-300'}
                      transition-transform
                    `}
                  >
                    {letter && (
                      <>
                        <span>{letter.toUpperCase()}</span>
                        <span className="absolute bottom-0.5 right-0.5 text-[10px] text-stone-600">{getTileValue(letter)}</span>
                      </>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-500 text-center">Waiting for game start...</p>
            )}

            <div className="grid grid-cols-2 gap-2 mb-2">
              <button
                onClick={handlePass}
                disabled={!isMyTurn || placedTiles.length > 0}
                className="bg-gray-200 p-2 rounded hover:bg-gray-300 disabled:opacity-50 text-sm font-medium"
              >
                Pass
              </button>
              <button
                onClick={handleSwap}
                disabled={!isMyTurn || placedTiles.length > 0}
                className="bg-gray-200 p-2 rounded hover:bg-gray-300 disabled:opacity-50 text-sm font-medium"
              >
                Swap
              </button>
            </div>
            <div className="flex flex-col gap-2">
              <button
                onClick={handleRecall}
                disabled={placedTiles.length === 0}
                className="flex items-center justify-center gap-2 bg-gray-200 p-2 rounded hover:bg-gray-300 disabled:opacity-50"
              >
                <RefreshCw size={16} /> Recall
              </button>
              <button
                onClick={handleSubmitTurn}
                disabled={!isMyTurn || placedTiles.length === 0}
                className="flex items-center justify-center gap-2 bg-blue-500 text-white p-2 rounded hover:bg-blue-600 disabled:opacity-50"
              >
                <Check size={16} /> Play
              </button>
            </div>
          </div>

        </div>
      </div>
    </div>
  )
}
