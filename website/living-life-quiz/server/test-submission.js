// Test script to verify the submission endpoint works correctly
import fetch from 'node-fetch'

const testSubmission = {
  studentName: "Test Student",
  startTime: new Date(Date.now() - 30 * 60 * 1000).toISOString(), // 30 minutes ago
  endTime: new Date().toISOString(),
  totalQuestions: 3,
  answers: [
    {
      questionId: "q1",
      answer: true,
      timestamp: new Date(Date.now() - 25 * 60 * 1000).toISOString(),
      questionIndex: 0
    },
    {
      questionId: "q2", 
      answer: ["Jesus", "Christ"],
      timestamp: new Date(Date.now() - 20 * 60 * 1000).toISOString(),
      questionIndex: 1
    },
    {
      questionId: "q3",
      answer: "This is a sample short answer response that demonstrates the system working correctly.",
      timestamp: new Date(Date.now() - 15 * 60 * 1000).toISOString(),
      questionIndex: 2
    }
  ]
}

async function testSubmissionEndpoint() {
  try {
    console.log('🧪 Testing submission endpoint...')
    
    const response = await fetch('http://localhost:3002/api/submit-test', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(testSubmission)
    })

    if (response.ok) {
      const result = await response.json()
      console.log('✅ Submission successful!')
      console.log('📊 Response:', JSON.stringify(result, null, 2))
    } else {
      const error = await response.text()
      console.error('❌ Submission failed:', response.status, error)
    }
  } catch (error) {
    console.error('❌ Network error:', error.message)
  }
}

// Test the health endpoint first
async function testHealthEndpoint() {
  try {
    console.log('🏥 Testing health endpoint...')
    const response = await fetch('http://localhost:3002/api/health')
    
    if (response.ok) {
      const result = await response.json()
      console.log('✅ Server is healthy!')
      console.log('📋 Health Status:', JSON.stringify(result, null, 2))
      return true
    } else {
      console.error('❌ Health check failed:', response.status)
      return false
    }
  } catch (error) {
    console.error('❌ Health check error:', error.message)
    return false
  }
}

// Run tests
async function runTests() {
  console.log('🚀 Starting server tests...\n')
  
  const isHealthy = await testHealthEndpoint()
  console.log('')
  
  if (isHealthy) {
    await testSubmissionEndpoint()
  } else {
    console.log('⚠️ Skipping submission test due to health check failure')
  }
  
  console.log('\n✨ Tests completed!')
}

runTests().catch(console.error)
