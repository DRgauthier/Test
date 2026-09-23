import { BOARD_SIZE, BOARD_LAYOUT, MULTIPLIERS } from './gameLogic';
import { isValidWord, getTileValue } from './wordValidation';

// Helper to check if it's the very first turn of the game
const isFirstTurn = (board) => {
  for (let r = 0; r < BOARD_SIZE; r++) {
    for (let c = 0; c < BOARD_SIZE; c++) {
      if (board[r][c] !== null) return false;
    }
  }
  return true;
};

// Main function to validate and score a move
export const validateAndScoreMove = (board, placedTiles) => {
  if (!placedTiles || placedTiles.length === 0) {
    return { valid: false, error: "No tiles placed." };
  }

  // 1. Check if all placed tiles are in the same row or column
  const rows = new Set(placedTiles.map(pt => pt.row));
  const cols = new Set(placedTiles.map(pt => pt.col));

  if (rows.size > 1 && cols.size > 1) {
    return { valid: false, error: "Tiles must be placed in a single row or column." };
  }

  const isHorizontal = rows.size === 1;

  // Sort placed tiles to find min and max
  const sortedTiles = [...placedTiles].sort((a, b) =>
    isHorizontal ? a.col - b.col : a.row - b.row
  );

  // 2. Check for gaps in the placed word (including existing tiles on the board)
  const first = sortedTiles[0];
  const last = sortedTiles[sortedTiles.length - 1];

  if (isHorizontal) {
    const row = first.row;
    for (let c = first.col; c <= last.col; c++) {
      if (board[row][c] === null && !placedTiles.find(pt => pt.row === row && pt.col === c)) {
        return { valid: false, error: "There cannot be gaps in the placed word." };
      }
    }
  } else {
    const col = first.col;
    for (let r = first.row; r <= last.row; r++) {
      if (board[r][col] === null && !placedTiles.find(pt => pt.row === r && pt.col === col)) {
        return { valid: false, error: "There cannot be gaps in the placed word." };
      }
    }
  }

  // 3. Connectivity Rules
  let isConnected = false;
  if (isFirstTurn(board)) {
    // Must cover center square (7,7)
    const centerCovered = placedTiles.some(pt => pt.row === 7 && pt.col === 7);
    if (!centerCovered) {
      return { valid: false, error: "The first word must cover the center square." };
    }
    isConnected = true;
  } else {
    // Must touch at least one existing tile on the board
    const directions = [[0,1], [1,0], [0,-1], [-1,0]];
    for (let pt of placedTiles) {
      for (let [dr, dc] of directions) {
        const nr = pt.row + dr;
        const nc = pt.col + dc;
        if (nr >= 0 && nr < BOARD_SIZE && nc >= 0 && nc < BOARD_SIZE) {
          if (board[nr][nc] !== null) {
            isConnected = true;
            break;
          }
        }
      }
      if (isConnected) break;
    }
    if (!isConnected) {
       return { valid: false, error: "New words must connect to existing tiles on the board." };
    }
  }

  // 4. Extract all formed words and score them
  let totalScore = 0;
  let allWords = [];

  // Temporary board with new tiles placed to make word extraction easier
  let tempBoard = board.map(row => [...row]);
  placedTiles.forEach(pt => {
    tempBoard[pt.row][pt.col] = pt.letter;
  });

  const getFullWord = (r, c, dRow, dCol) => {
    // find start
    let startR = r;
    let startC = c;
    while(startR - dRow >= 0 && startC - dCol >= 0 && tempBoard[startR - dRow][startC - dCol] !== null) {
      startR -= dRow;
      startC -= dCol;
    }

    // traverse to end
    let currentR = startR;
    let currentC = startC;
    let wordStr = '';
    let wordScore = 0;
    let wordMultiplier = 1;
    let includesNewTile = false;

    while(currentR < BOARD_SIZE && currentC < BOARD_SIZE && tempBoard[currentR][currentC] !== null) {
      const letter = tempBoard[currentR][currentC];
      wordStr += letter;

      let tileScore = getTileValue(letter);

      // Check if this tile is newly placed to apply board multipliers
      const newTile = placedTiles.find(pt => pt.row === currentR && pt.col === currentC);
      if (newTile) {
        includesNewTile = true;
        const squareMult = BOARD_LAYOUT[currentR][currentC];
        if (squareMult === MULTIPLIERS.DL) tileScore *= 2;
        if (squareMult === MULTIPLIERS.TL) tileScore *= 3;
        if (squareMult === MULTIPLIERS.DW) wordMultiplier *= 2;
        if (squareMult === MULTIPLIERS.TW) wordMultiplier *= 3;
      }

      wordScore += tileScore;

      currentR += dRow;
      currentC += dCol;
    }

    if (wordStr.length > 1 && includesNewTile) {
      return { word: wordStr, score: wordScore * wordMultiplier };
    }
    return null;
  };

  // Check the main axis (the direction the tiles were placed in, or horizontal if 1 tile)
  const mainAxis = isHorizontal ? [0, 1] : [1, 0];
  const mainWord = getFullWord(first.row, first.col, mainAxis[0], mainAxis[1]);
  if (mainWord) {
    allWords.push(mainWord);
  }

  // Check cross axes for each placed tile
  const crossAxis = isHorizontal ? [1, 0] : [0, 1];
  for (let pt of placedTiles) {
    const crossWord = getFullWord(pt.row, pt.col, crossAxis[0], crossAxis[1]);
    if (crossWord) {
      allWords.push(crossWord);
    }
  }

  // If no words > 1 letter formed, invalid move
  if (allWords.length === 0) {
    return { valid: false, error: "Must form at least one word." };
  }

  // 5. Validate all formed words against dictionary
  for (let w of allWords) {
    if (!isValidWord(w.word)) {
      return { valid: false, error: `'${w.word}' is not a valid word in the dictionary.` };
    }
    totalScore += w.score;
  }

  // Bingo bonus (50 points for placing all 7 tiles)
  if (placedTiles.length === 7) {
    totalScore += 50;
  }

  return { valid: true, score: totalScore, words: allWords.map(w => w.word) };
};
