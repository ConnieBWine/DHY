import React, { useState, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import AIChatbox from '../components/AIChatbox';
import { WorkoutContext } from '../context/WorkoutContext';

const AI = () => {
  const { setWorkoutPlan } = useContext(WorkoutContext);
  const [generatedPlan, setGeneratedPlan] = useState(null);
  const navigate = useNavigate();
  
  // Handle generated workout plan from AI
  const handleWorkoutPlanGenerated = (plan) => {
    setGeneratedPlan(plan);
    setWorkoutPlan(plan);
  };
  
  // Navigate to workout page to use the plan
  const handleUsePlan = () => {
    navigate('/workout');
  };
  
  // Sample prompts for generating workout plans
  const samplePrompts = [
    "Create a 7-day workout plan for a beginner focused on full body strength.",
    "I need a workout plan for weight loss with minimal equipment.",
    "Generate a workout plan for improving cardiovascular fitness.",
    "Create a bodyweight workout plan I can do at home with no equipment.",
    "I want a workout plan to improve my core strength and stability."
  ];
  
  // Copy prompt to clipboard
  const copyPrompt = (prompt) => {
    navigator.clipboard.writeText(prompt);
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">AI Workout Coach</h1>
      
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main chat area */}
        <div className="lg:col-span-2">
          <div className="card h-[600px] flex flex-col">
            <AIChatbox 
              onWorkoutPlanGenerated={handleWorkoutPlanGenerated}
              className="h-full"
            />
          </div>
        </div>
        
        {/* Sidebar with sample prompts and plan preview */}
        <div className="space-y-6">
          {/* Sample prompts */}
          <div className="card">
            <h2 className="text-xl font-bold mb-4">Sample Prompts</h2>
            <div className="space-y-3">
              {samplePrompts.map((prompt, index) => (
                <div 
                  key={index}
                  className="p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition cursor-pointer flex justify-between items-start"
                  onClick={() => copyPrompt(prompt)}
                >
                  <p className="text-sm">{prompt}</p>
                  <button className="ml-2 text-gray-500 hover:text-primary-600">
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    </svg>
                  </button>
                </div>
              ))}
            </div>
            <p className="text-xs text-gray-500 mt-4">Click on a prompt to copy it to the clipboard, then paste it in the chat.</p>
          </div>
          
          {/* Generated plan preview */}
          {generatedPlan && (
            <div className="card">
              <h2 className="text-xl font-bold mb-4">Generated Plan</h2>
              <div className="max-h-64 overflow-y-auto pr-2">
                {generatedPlan.map((day, dayIndex) => (
                  <div key={dayIndex} className="mb-3">
                    <h3 className="font-semibold text-primary-700">{day.day}</h3>
                    <ul className="list-disc list-inside pl-2">
                      {day.exercises.map((exercise, exIndex) => (
                        <li key={exIndex} className="text-sm">
                          <span className="font-medium">{exercise.name}:</span> {' '}
                          {exercise.is_timed 
                            ? `${exercise.reps} seconds`
                            : `${exercise.sets} x ${exercise.reps}`}
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
              
              <button 
                className="btn btn-primary w-full mt-4"
                onClick={handleUsePlan}
              >
                Use This Plan
              </button>
            </div>
          )}
          
          {/* Tips section */}
          <div className="card bg-primary-50 border border-primary-100">
            <h2 className="text-xl font-bold mb-4 text-primary-800">Coach Tips</h2>
            <ul className="space-y-2 text-primary-700">
              <li className="flex items-start">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2 mt-0.5 text-primary-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span>Be specific about your fitness level (beginner, intermediate, advanced).</span>
              </li>
              <li className="flex items-start">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2 mt-0.5 text-primary-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span>Mention any equipment you have available.</span>
              </li>
              <li className="flex items-start">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2 mt-0.5 text-primary-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span>Include your fitness goals (strength, weight loss, endurance, etc.).</span>
              </li>
              <li className="flex items-start">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2 mt-0.5 text-primary-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span>Specify how many days per week you want to work out.</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AI;