/**
 * Shared scoring logic for quiz questions
 * This module can be used by both frontend (browser) and backend (Node.js)
 */

// Helper function to compare strings case-insensitively
const compareStrings = (str1, str2) => {
  if (!str1 || !str2) return false
  return str1.toLowerCase().trim() === str2.toLowerCase().trim()
}

// Calculate score for a single question
const calculateQuestionScore = (question, userAnswer) => {
  // Special handling for TRUE_FALSE questions - null means no answer, but false/true are valid
  if (question.type === 'TRUE_FALSE') {
    if (userAnswer === null || userAnswer === undefined) {
      return 0 // No answer provided
    }
    // For TRUE_FALSE, both true and false are valid answers, proceed to scoring
  } else {
    // For other question types, check for empty values (excluding boolean false)
    if (userAnswer === null || userAnswer === undefined || userAnswer === '' || 
        (Array.isArray(userAnswer) && userAnswer.every(a => !a || !a.trim()))) {
      return 0 // No answer provided
    }
  }

  switch (question.type) {
    case 'TRUE_FALSE':
      const correctAnswer = question.correct_answer
      return userAnswer === correctAnswer ? question.points : 0

    case 'SIMPLE_FILL_IN_THE_BLANK':
      if (Array.isArray(userAnswer)) {
        // Multiple answers - flexible matching with uniqueness enforcement
        const matchedCorrectAnswers = new Set() // Track which correct answers have been matched
        let correctCount = 0
        
        for (const answer of userAnswer) {
          if (!answer || !answer.trim()) continue // Skip empty answers
          
          // Find a correct answer that matches and hasn't been used yet
          for (const correct of question.correct_answers) {
            if (!matchedCorrectAnswers.has(correct) && compareStrings(answer, correct)) {
              matchedCorrectAnswers.add(correct)
              correctCount++
              break // Move to next user answer
            }
          }
        }
        
        // Partial credit: points distributed across all expected answers
        const pointsPerAnswer = question.points / question.correct_answers.length
        return correctCount * pointsPerAnswer
      } else {
        // Single answer
        return question.correct_answers.some(correct => compareStrings(userAnswer, correct)) 
          ? question.points : 0
      }

    case 'STRUCTURED_FILL_IN_THE_BLANK':
      if (!Array.isArray(userAnswer)) return 0
      const correctParts = question.parts.filter((part, index) => 
        userAnswer[index] && compareStrings(userAnswer[index], part.correct_answer)
      ).length
      
      // Partial credit: points distributed across all parts
      const pointsPerPart = question.points / question.parts.length
      return correctParts * pointsPerPart

    case 'SHORT_ANSWER':
      // Short answers always get full points if non-empty (require manual grading)
      return userAnswer && userAnswer.trim().length > 0 ? question.points : 0

    default:
      return 0
  }
}

// Check if an answer is completely correct (full points)
const isAnswerCorrect = (question, userAnswer) => {
  const score = calculateQuestionScore(question, userAnswer)
  return score === question.points
}

// Check if an answer is partially correct (some points but not full)
const isAnswerPartiallyCorrect = (question, userAnswer) => {
  const score = calculateQuestionScore(question, userAnswer)
  return score > 0 && score < question.points
}

// ES6 module exports (for Node.js and bundlers)
export {
  compareStrings,
  calculateQuestionScore,
  isAnswerCorrect,
  isAnswerPartiallyCorrect
}

// Browser global fallback (for direct script inclusion)
if (typeof window !== 'undefined') {
  window.ScoringLogic = {
    compareStrings,
    calculateQuestionScore,
    isAnswerCorrect,
    isAnswerPartiallyCorrect
  }
}
