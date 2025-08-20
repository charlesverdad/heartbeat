Question Types

1. Simple Fill in the Blank: These questions pose a single prompt and expect one or more concise, direct answers, often presented as a numbered list in the source.
    ◦ Example: "Write down the three definitions of sin found in the New Testament."
    ◦ Example: "What are the five components of prayer?"

2. Structured Fill in the Blank: These questions act as a main heading or topic, under which multiple sub-questions or specific prompts are listed, each requiring a distinct short answer. This type is used when the main question introduces a set of related facts or details to be provided.
    ◦ Example: "In regards to the books of the Bible:" followed by sub-questions like "1. How many books are in the Old Testament?"
    ◦ Example: "In regards to Jesus Christ:" followed by sub-questions like "1. Which tribe is he from?"

3. True/False: These questions present a statement that the user must determine as either true or false. The source explicitly marks the correct answer with (T) or (F).
    ◦ Example: "(T) The most important thing in Christian life is having the right relationship with God and neighbors."
    ◦ Example: "(F) The reason why Jesus died on the cross is for his sins as well as for ours."

4. Short Answer (Open-Ended): This type is characterized by questions that prompt a subjective or reflective answer, where the correct response isn't fixed but rather depends on the user's personal thought or experience. Scoring for this type would likely require manual review or be completion-based (e.g., points awarded for any non-empty, relevant response) rather than automated correctness checking.
    ◦ Example: "Write down what you think your spiritual gifts are and why."

Question Class Schema

Below is a JSON Schema definition for a generic Question class and its different types. This schema allows you to structure your question data, ensuring consistency and making it easier for your website to parse and score.
Note: The JSON Schema syntax itself, and the use of discriminator for type differentiation, are concepts external to the provided source material but are standard practices for defining structured data schemas.

{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Question Schema",
  "description": "Schema for various question types in a quiz system based on the LLBS document.",
  "type": "object",
  "properties": {
    "id": {
      "type": "string",
      "description": "Unique identifier for the question. E.g., 'q1_sin_definitions'."
    },
    "type": {
      "type": "string",
      "description": "The type of question.",
      "enum": [
        "SIMPLE_FILL_IN_THE_BLANK",
        "STRUCTURED_FILL_IN_THE_BLANK",
        "TRUE_FALSE",
        "SHORT_ANSWER"
      ]
    },
    "question_text": {
      "type": "string",
      "description": "The main text or prompt of the question."
    },
    "points": {
      "type": "integer",
      "description": "Total points awarded for correctly answering this question. This is defined per question number in the source."
    },
    "citation": {
      "type": "string",
      "description": "Optional biblical citation for the question, if provided in the source."
    }
  },
  "required": ["id", "type", "question_text", "points"],
  "discriminator": {
    "propertyName": "type",
    "mapping": {
      "SIMPLE_FILL_IN_THE_BLANK": "#/definitions/SimpleFillInTheBlankQuestion",
      "STRUCTURED_FILL_IN_THE_BLANK": "#/definitions/StructuredFillInTheBlankQuestion",
      "TRUE_FALSE": "#/definitions/TrueFalseQuestion",
      "SHORT_ANSWER": "#/definitions/ShortAnswerQuestion"
    }
  },
  "definitions": {
    "SimpleFillInTheBlankQuestion": {
      "type": "object",
      "description": "A question where the user fills in one or more blanks directly related to the main question text. Answers are typically short and listed.",
      "properties": {
        "type": { "const": "SIMPLE_FILL_IN_THE_BLANK" },
        "correct_answers": {
          "type": "array",
          "items": { "type": "string" },
          "description": "A list of expected correct answers. The order matters if the question implicitly or explicitly lists items (e.g., 'first, second, third definition')."
        }
      },
      "required": ["correct_answers"]
    },
    "StructuredFillInTheBlankQuestion": {
      "type": "object",
      "description": "A question that acts as a header for multiple sub-parts, each with its own prompt and requiring a specific short answer.",
      "properties": {
        "type": { "const": "STRUCTURED_FILL_IN_THE_BLANK" },
        "parts": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "prompt": { "type": "string", "description": "The specific sub-prompt or question for this part (e.g., '1. How many books...')." },
              "correct_answer": { "type": "string", "description": "The correct answer for this specific sub-part." },
              "citation": { "type": "string", "description": "Optional biblical citation specific to this sub-part." }
            },
            "required": ["prompt", "correct_answer"]
          },
          "description": "An array of individual sub-questions or facts that make up this structured question."
        }
      },
      "required": ["parts"]
    },
    "TrueFalseQuestion": {
      "type": "object",
      "description": "A question requiring a 'True' or 'False' answer.",
      "properties": {
        "type": { "const": "TRUE_FALSE" },
        "correct_answer": {
          "type": "boolean",
          "description": "The correct answer: `true` for 'T', `false` for 'F'."
        }
      },
      "required": ["correct_answer"]
    },
    "ShortAnswerQuestion": {
      "type": "object",
      "description": "A question requiring a subjective or open-ended text answer, typically requiring manual grading.",
      "properties": {
        "type": { "const": "SHORT_ANSWER" },
        "grading_notes": {
          "type": "string",
          "description": "Notes for how this question should be graded, e.g., 'Requires manual review; points for thoughtful, relevant answer.'"
        }
      }
    }
  }
}
Examples of Question Data using the Schema
Here are examples of how questions from your source material would be represented using this schema:

1. Simple Fill in the Blank Question Example
• Source: "1. Write down the three definitions of sin found in the New Testament. (3 pts.) 1. Lawlessness 2. Knowing the good we ought to do and are not doing it 3. Everything that doesn’t come from faith"
{
  "id": "q1_sin_definitions",
  "type": "SIMPLE_FILL_IN_THE_BLANK",
  "question_text": "Write down the three definitions of sin found in the New Testament.",
  "points": 3,
  "correct_answers": [
    "Lawlessness",
    "Knowing the good we ought to do and are not doing it",
    "Everything that doesn’t come from faith"
  ]
}

2. Structured Fill in the Blank Question Example
• Source: "3. In regards to the books of the Bible: (4 pts.) 1. How many books are in the Old Testament? 39 books 2. How many books are in the New Testament? 27 books 3. When was the Old Testament completed? 400 BC 4. When was the New Testament completed? AD 90"
{
  "id": "q3_bible_books_details",
  "type": "STRUCTURED_FILL_IN_THE_BLANK",
  "question_text": "In regards to the books of the Bible:",
  "points": 4,
  "parts": [
    {
      "prompt": "1. How many books are in the Old Testament?",
      "correct_answer": "39 books"
    },
    {
      "prompt": "2. How many books are in the New Testament?",
      "correct_answer": "27 books"
    },
    {
      "prompt": "3. When was the Old Testament completed?",
      "correct_answer": "400 BC"
    },
    {
      "prompt": "4. When was the New Testament completed?",
      "correct_answer": "AD 90"
    }
  ]
}

3. True/False Question Example
• Source: "(T) The most important thing in Christian life is having the right relationship with God and neighbors. (Matthew 22: 34-40)"
{
  "id": "tf1_relationship_importance",
  "type": "TRUE_FALSE",
  "question_text": "The most important thing in Christian life is having the right relationship with God and neighbors.",
  "points": 1,
  "correct_answer": true,
  "citation": "Matthew 22: 34-40"
}
4. Short Answer Question Example
• Source: "12. Write down what you think your spiritual gifts are and why. (1 pt.)"
{
  "id": "q12_spiritual_gifts",
  "type": "SHORT_ANSWER",
  "question_text": "Write down what you think your spiritual gifts are and why.",
  "points": 1,
  "grading_notes": "This question requires manual review. Points may be awarded for a thoughtful, relevant answer."
}
This schema provides a flexible and structured way to represent the various question formats found in your source document, which should facilitate the design and implementation of your scoring website.