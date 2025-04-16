import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

const WorkoutPlan = ({ workoutPlan, onSelectExercise }) => {
  const [activeDay, setActiveDay] = useState(0);
  const navigate = useNavigate();
  
  // Check if we have a valid workout plan
  const hasWorkoutPlan = workoutPlan && 
                         Array.isArray(workoutPlan) && 
                         workoutPlan.length > 0;
  
  // Handle exercise selection
  const handleSelectExercise = (exercise) => {
    if (onSelectExercise) {
      onSelectExercise(
        exercise.name,
        exercise.is_timed ? 0 : exercise.reps,
        exercise.sets,
        exercise.is_timed ? exercise.reps : 0
      );
      
      // Navigate to workout page if we're not already there
      navigate('/workout');
    }
  };
  
  return (
    <div className="card">
      <h2 className="text-xl font-bold mb-4">Workout Plan</h2>
      
      {hasWorkoutPlan ? (
        <div>
          {/* Day selector tabs */}
          <div className="flex overflow-x-auto space-x-2 pb-2 mb-4">
            {workoutPlan.map((day, index) => (
              <button
                key={index}
                className={`px-4 py-2 rounded-md text-sm font-medium whitespace-nowrap ${
                  activeDay === index
                    ? 'bg-primary-600 text-white'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
                onClick={() => setActiveDay(index)}
              >
                {day.day}
              </button>
            ))}
          </div>
          
          {/* Active day exercises */}
          <div className="space-y-4">
            {workoutPlan[activeDay].exercises.map((exercise, index) => (
              <div 
                key={index}
                className="p-4 border border-gray-200 rounded-lg hover:border-primary-300 transition-colors"
              >
                <div className="flex justify-between items-center">
                  <div>
                    <h3 className="font-semibold text-lg">{exercise.name}</h3>
                    <p className="text-gray-600">
                      {exercise.is_timed
                        ? `${exercise.reps} seconds`
                        : `${exercise.sets} sets × ${exercise.reps} reps`}
                    </p>
                  </div>
                  
                  <button
                    className="btn btn-primary"
                    onClick={() => handleSelectExercise(exercise)}
                  >
                    Start
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="text-center py-8">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-12 w-12 mx-auto text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
          </svg>
          <p className="text-gray-500 mt-4">No workout plan available. Use the AI Coach to generate a plan.</p>
          
          <button
            className="btn btn-primary mt-4"
            onClick={() => navigate('/ai')}
          >
            Go to AI Coach
          </button>
        </div>
      )}
    </div>
  );
};

export default WorkoutPlan;