import dictionaryList from './dictionary.json';
import { LETTER_DISTRIBUTION } from './gameLogic';

const dictionarySet = new Set(dictionaryList);

export const isValidWord = (word) => {
  return dictionarySet.has(word.toUpperCase());
};

export const getTileValue = (letter) => {
    if (!letter || letter === '_') return 0;
    // Lowercase means it's a blank tile acting as a letter
    if (letter === letter.toLowerCase()) return 0;

    return LETTER_DISTRIBUTION[letter.toUpperCase()]?.value || 0;
};
