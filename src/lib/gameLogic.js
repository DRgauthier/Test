export const BOARD_SIZE = 15;

export const MULTIPLIERS = {
  TW: 'TW', // Triple Word
  DW: 'DW', // Double Word
  TL: 'TL', // Triple Letter
  DL: 'DL', // Double Letter
  NONE: null
};

// Standard Scrabble board layout
// Symmetric, so we only need to define a quarter or specify explicit coordinates.
export const BOARD_LAYOUT = Array(BOARD_SIZE).fill(null).map(() => Array(BOARD_SIZE).fill(MULTIPLIERS.NONE));

const setMultiplier = (coords, type) => {
  coords.forEach(([r, c]) => {
    BOARD_LAYOUT[r][c] = type;
    BOARD_LAYOUT[r][BOARD_SIZE - 1 - c] = type;
    BOARD_LAYOUT[BOARD_SIZE - 1 - r][c] = type;
    BOARD_LAYOUT[BOARD_SIZE - 1 - r][BOARD_SIZE - 1 - c] = type;
  });
};

// TW
setMultiplier([[0, 0], [0, 7]], MULTIPLIERS.TW);
// DW
setMultiplier([[1, 1], [2, 2], [3, 3], [4, 4], [7, 7]], MULTIPLIERS.DW);
// TL
setMultiplier([[1, 5], [5, 1], [5, 5]], MULTIPLIERS.TL);
// DL
setMultiplier([[0, 3], [2, 6], [3, 0], [3, 7], [6, 2], [6, 6], [7, 3]], MULTIPLIERS.DL);


export const LETTER_DISTRIBUTION = {
  'A': { count: 9, value: 1 },
  'B': { count: 2, value: 3 },
  'C': { count: 2, value: 3 },
  'D': { count: 4, value: 2 },
  'E': { count: 12, value: 1 },
  'F': { count: 2, value: 4 },
  'G': { count: 3, value: 2 },
  'H': { count: 2, value: 4 },
  'I': { count: 9, value: 1 },
  'J': { count: 1, value: 8 },
  'K': { count: 1, value: 5 },
  'L': { count: 4, value: 1 },
  'M': { count: 2, value: 3 },
  'N': { count: 6, value: 1 },
  'O': { count: 8, value: 1 },
  'P': { count: 2, value: 3 },
  'Q': { count: 1, value: 10 },
  'R': { count: 6, value: 1 },
  'S': { count: 4, value: 1 },
  'T': { count: 6, value: 1 },
  'U': { count: 4, value: 1 },
  'V': { count: 2, value: 4 },
  'W': { count: 2, value: 4 },
  'X': { count: 1, value: 8 },
  'Y': { count: 2, value: 4 },
  'Z': { count: 1, value: 10 },
  '_': { count: 2, value: 0 }, // Blank tile
};

export const createTileBag = () => {
  const bag = [];
  for (const [letter, data] of Object.entries(LETTER_DISTRIBUTION)) {
    for (let i = 0; i < data.count; i++) {
      bag.push(letter);
    }
  }
  // Shuffle
  for (let i = bag.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [bag[i], bag[j]] = [bag[j], bag[i]];
  }
  return bag;
};

export const drawTiles = (bag, count) => {
  const drawn = [];
  for (let i = 0; i < count && bag.length > 0; i++) {
    drawn.push(bag.pop());
  }
  return drawn;
};
