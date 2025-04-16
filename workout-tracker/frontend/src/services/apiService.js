import axios from 'axios';

// Base URL for API requests
const API_BASE_URL = 'http://localhost:8000/api';

// Create an axios instance with default config
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// API service functions
const apiService = {
  // Survey and workout plan functions
  submitSurvey: async (surveyData) => {
    try {
      const response = await apiClient.post('/workout-plan', surveyData);
      return response.data;
    } catch (error) {
      console.error('Error submitting survey:', error);
      throw error;
    }
  },

  getCustomWorkoutPlan: async (prompt) => {
    try {
      const response = await apiClient.post('/workout-prompt', { prompt });
      return response.data;
    } catch (error) {
      console.error('Error getting custom workout plan:', error);
      throw error;
    }
  },

  // Exercise tracking functions
  getAvailableExercises: async () => {
    try {
      const response = await apiClient.get('/exercises');
      return response.data.exercises;
    } catch (error) {
      console.error('Error fetching exercises:', error);
      throw error;
    }
  },

  startExercise: async (exerciseData) => {
    try {
      const response = await apiClient.post('/start-exercise', exerciseData);
      return response.data;
    } catch (error) {
      console.error('Error starting exercise:', error);
      throw error;
    }
  },

  // AI chat functions
  sendChatMessage: async (message) => {
    try {
      const response = await apiClient.post('/chat', { message });
      return response.data;
    } catch (error) {
      console.error('Error sending chat message:', error);
      throw error;
    }
  },

  // Session statistics functions
  getSessionStats: async () => {
    try {
      const response = await apiClient.get('/session-stats');
      return response.data;
    } catch (error) {
      console.error('Error fetching session stats:', error);
      throw error;
    }
  },

  // Utility function to handle errors
  handleApiError: (error) => {
    let errorMessage = 'An unexpected error occurred';
    
    if (error.response) {
      // The request was made and the server responded with a status code
      // that falls out of the range of 2xx
      console.error('Error response:', error.response.data);
      errorMessage = error.response.data.detail || 'Server error: ' + error.response.status;
    } else if (error.request) {
      // The request was made but no response was received
      console.error('Error request:', error.request);
      errorMessage = 'No response from server. Please check your internet connection.';
    } else {
      // Something happened in setting up the request that triggered an Error
      console.error('Error message:', error.message);
      errorMessage = error.message;
    }
    
    return errorMessage;
  }
};

export default apiService;