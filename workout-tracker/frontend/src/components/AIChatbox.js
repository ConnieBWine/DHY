import React, { useState, useRef, useEffect } from 'react';
import apiService from '../services/apiService';

const AIChatbox = ({ onWorkoutPlanGenerated, className = '' }) => {
  // State for chat messages and input
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  
  // Ref for auto-scrolling chat
  const chatContainerRef = useRef(null);

  // Add system welcome message on initial render
  useEffect(() => {
    setMessages([
      {
        id: 'welcome',
        sender: 'ai',
        text: 'Hello! I\'m your workout AI assistant. I can help you create a customized workout plan based on your goals and fitness level. What type of workout are you looking for today?',
        timestamp: new Date()
      }
    ]);
  }, []);

  // Auto-scroll to bottom of chat when messages change
  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [messages]);

  // Send message to AI
  const sendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return;
    
    const userMessage = {
      id: Date.now().toString(),
      sender: 'user',
      text: inputMessage,
      timestamp: new Date()
    };
    
    // Add user message to chat
    setMessages(prevMessages => [...prevMessages, userMessage]);
    setInputMessage('');
    setError(null);
    setIsLoading(true);
    
    try {
      // Check if message is related to workout plan generation
      const isWorkoutRequest = 
        inputMessage.toLowerCase().includes('workout plan') || 
        inputMessage.toLowerCase().includes('exercise plan') ||
        inputMessage.toLowerCase().includes('fitness plan');
      
      if (isWorkoutRequest) {
        // Use specialized endpoint for workout plans
        const response = await apiService.getCustomWorkoutPlan(inputMessage);
        
        // Add AI response to chat
        const aiMessage = {
          id: `ai-${Date.now()}`,
          sender: 'ai',
          text: response.raw_response || 'I\'ve created a workout plan for you!',
          timestamp: new Date(),
          workoutPlan: response.workout_plan
        };
        
        setMessages(prevMessages => [...prevMessages, aiMessage]);
        
        // Notify parent component about generated workout plan
        if (response.workout_plan && onWorkoutPlanGenerated) {
          onWorkoutPlanGenerated(response.workout_plan);
        }
      } else {
        // Use regular chat endpoint for other messages
        const response = await apiService.sendChatMessage(inputMessage);
        
        // Add AI response to chat
        const aiMessage = {
          id: `ai-${Date.now()}`,
          sender: 'ai',
          text: response.message || 'I understand your message, but I\'m having trouble formulating a response.',
          timestamp: new Date()
        };
        
        setMessages(prevMessages => [...prevMessages, aiMessage]);
      }
    } catch (err) {
      console.error('Error sending message:', err);
      setError(apiService.handleApiError(err));
      
      // Add error message to chat
      const errorMessage = {
        id: `error-${Date.now()}`,
        sender: 'system',
        text: 'Sorry, I encountered an error processing your request. Please try again.',
        timestamp: new Date(),
        isError: true
      };
      
      setMessages(prevMessages => [...prevMessages, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  // Handle Enter key press
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  // Format workout plan display
  const formatWorkoutPlan = (plan) => {
    if (!plan || !Array.isArray(plan)) return null;
    
    return (
      <div className="bg-gray-50 p-3 rounded-md mt-2 text-sm">
        <h3 className="font-bold text-primary-700 mb-2">Workout Plan</h3>
        
        {plan.map((day, index) => (
          <div key={index} className="mb-3">
            <h4 className="font-semibold">{day.day}</h4>
            <ul className="list-disc list-inside pl-2">
              {day.exercises.map((exercise, exIndex) => (
                <li key={exIndex}>
                  <span className="font-medium">{exercise.name}:</span> {' '}
                  {exercise.is_timed 
                    ? `${exercise.reps} seconds`
                    : `${exercise.sets} x ${exercise.reps}`}
                </li>
              ))}
            </ul>
          </div>
        ))}
        
        <button 
          onClick={() => onWorkoutPlanGenerated(plan)}
          className="btn btn-sm btn-primary w-full mt-2"
        >
          Use This Plan
        </button>
      </div>
    );
  };

  return (
    <div className={`flex flex-col h-full ${className}`}>
      <div className="card flex-1 flex flex-col overflow-hidden">
        <h2 className="text-xl font-bold mb-4">AI Coach</h2>
        
        {/* Chat messages container */}
        <div 
          ref={chatContainerRef}
          className="flex-1 overflow-y-auto mb-4 space-y-4 p-2"
        >
          {messages.map(message => (
            <div 
              key={message.id}
              className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div 
                className={`max-w-3/4 rounded-lg px-4 py-2 ${
                  message.sender === 'user'
                    ? 'bg-primary-600 text-white'
                    : message.sender === 'ai'
                      ? 'bg-gray-100 text-gray-800'
                      : 'bg-error-100 text-error-800'
                }`}
              >
                <div className="text-sm">{message.text}</div>
                
                {/* Render workout plan if available */}
                {message.workoutPlan && formatWorkoutPlan(message.workoutPlan)}
              </div>
            </div>
          ))}
          
          {/* Loading indicator */}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-gray-100 rounded-lg px-4 py-2">
                <div className="flex space-x-1">
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
                </div>
              </div>
            </div>
          )}
        </div>
        
        {/* Error display */}
        {error && (
          <div className="mb-4 p-2 bg-error-100 text-error-800 rounded-md text-sm">
            {error}
          </div>
        )}
        
        {/* Message input */}
        <div className="flex items-center">
          <textarea
            className="form-input py-2 resize-none flex-1"
            placeholder="Type your message..."
            rows="2"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            disabled={isLoading}
          />
          <button
            className="btn btn-primary ml-2 h-full"
            onClick={sendMessage}
            disabled={isLoading || !inputMessage.trim()}
          >
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" className="h-5 w-5">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
};

export default AIChatbox;