import React, { useState, useEffect, useContext } from 'react';
import { WorkoutContext } from '../context/WorkoutContext';

const ExerciseControls = ({ 
  onExerciseChange, 
  currentExercise,
  exerciseData,
  className = '' 
}) => {
  const { exerciseList } = useContext(WorkoutContext);
  
  // Local state for exercise configuration
  const [exercise, setExercise] = useState(currentExercise || '');
  const [targetReps, setTargetReps] = useState(10);
  const [targetSets, setTargetSets] = useState(3);
  const [targetDuration, setTargetDuration] = useState(60);
  const [isActive, setIsActive] = useState(false);
  const [selectedExerciseType, setSelectedExerciseType] = useState('reps');

  // Handle exercise selection change
  const handleExerciseChange = (e) => {
    const selectedExercise = e.target.value;
    setExercise(selectedExercise);
    
    // Update exercise type based on selection
    const selectedType = exerciseList.find(ex => ex.name === selectedExercise)?.type || 'reps';
    setSelectedExerciseType(selectedType);
    
    // Reset target values
    if (selectedType === 'timed') {
      setTargetReps(0);
    } else {
      setTargetDuration(0);
    }
  };

  // Start exercise tracking
  const handleStartExercise = () => {
    if (!exercise) return;
    
    setIsActive(true);
    onExerciseChange(exercise, targetReps, targetSets, targetDuration);
  };

  // Stop exercise tracking
  const handleStopExercise = () => {
    setIsActive(false);
    onExerciseChange(null);
  };

  // Update component when current exercise changes
  useEffect(() => {
    if (currentExercise) {
      setExercise(currentExercise);
      setIsActive(true);
      
      // Update exercise type
      const type = exerciseList.find(ex => ex.name.toLowerCase() === currentExercise.toLowerCase())?.type || 'reps';
      setSelectedExerciseType(type);
    } else {
      setIsActive(false);
    }
  }, [currentExercise, exerciseList]);

  return (
    <div className={`${className}`}>
      <div className="card">
        <h2 className="text-xl font-bold mb-4">Exercise Controls</h2>
        
        {!isActive ? (
          // Exercise setup form
          <div className="space-y-4">
            <div>
              <label htmlFor="exercise" className="form-label">Select Exercise</label>
              <select 
                id="exercise" 
                className="form-select"
                value={exercise}
                onChange={handleExerciseChange}
              >
                <option value="">Select an exercise</option>
                {exerciseList.map((ex) => (
                  <option key={ex.name} value={ex.name}>{ex.name}</option>
                ))}
              </select>
            </div>
            
            {exercise && (
              <>
                {selectedExerciseType === 'reps' ? (
                  <>
                    <div>
                      <label htmlFor="targetReps" className="form-label">Target Reps</label>
                      <input 
                        type="number" 
                        id="targetReps" 
                        className="form-input"
                        min="1"
                        value={targetReps}
                        onChange={(e) => setTargetReps(parseInt(e.target.value) || 0)}
                      />
                    </div>
                    
                    <div>
                      <label htmlFor="targetSets" className="form-label">Target Sets</label>
                      <input 
                        type="number" 
                        id="targetSets" 
                        className="form-input"
                        min="1"
                        value={targetSets}
                        onChange={(e) => setTargetSets(parseInt(e.target.value) || 1)}
                      />
                    </div>
                  </>
                ) : (
                  <div>
                    <label htmlFor="targetDuration" className="form-label">Duration (seconds)</label>
                    <input 
                      type="number" 
                      id="targetDuration" 
                      className="form-input"
                      min="5"
                      step="5"
                      value={targetDuration}
                      onChange={(e) => setTargetDuration(parseInt(e.target.value) || 0)}
                    />
                  </div>
                )}
                
                <button 
                  className="btn btn-primary w-full mt-4"
                  onClick={handleStartExercise}
                >
                  Start Exercise
                </button>
              </>
            )}
          </div>
        ) : (
          // Active exercise display
          <div className="space-y-4">
            <div className="bg-primary-100 rounded-lg p-4">
              <h3 className="font-bold text-primary-800">
                {exercise}
              </h3>
              
              {selectedExerciseType === 'reps' ? (
                <div className="mt-2">
                  <div className="text-3xl font-bold text-center">
                    {exerciseData?.rep_count || 0} 
                    <span className="text-sm text-gray-500 ml-1">/ {targetReps}</span>
                  </div>
                  
                  <div className="flex justify-between text-sm text-gray-700 mt-2">
                    <span>Set: {exerciseData?.current_set || 1} / {targetSets}</span>
                    <span>State: {exerciseData?.state || 'IDLE'}</span>
                  </div>
                  
                  {/* Progress bar */}
                  <div className="w-full bg-gray-200 rounded-full h-2.5 mt-2">
                    <div 
                      className="bg-primary-600 h-2.5 rounded-full transition-all duration-300"
                      style={{ width: `${Math.min(100, ((exerciseData?.rep_count || 0) / targetReps) * 100)}%` }}
                    ></div>
                  </div>
                </div>
              ) : (
                <div className="mt-2">
                  <div className="text-3xl font-bold text-center">
                    {Math.floor(exerciseData?.elapsed_time || 0)}s
                    <span className="text-sm text-gray-500 ml-1">/ {targetDuration}s</span>
                  </div>
                  
                  <div className="text-sm text-gray-700 text-center mt-2">
                    <span>Remaining: {Math.ceil(exerciseData?.remaining_time || 0)}s</span>
                  </div>
                  
                  {/* Progress bar */}
                  <div className="w-full bg-gray-200 rounded-full h-2.5 mt-2">
                    <div 
                      className="bg-primary-600 h-2.5 rounded-full transition-all duration-300"
                      style={{ width: `${Math.min(100, ((exerciseData?.elapsed_time || 0) / targetDuration) * 100)}%` }}
                    ></div>
                  </div>
                </div>
              )}
              
              {/* Feedback display */}
              {exerciseData?.feedback?.length > 0 && (
                <div className="mt-4 p-3 bg-white rounded-lg shadow-sm">
                  <h4 className="text-sm font-semibold text-gray-700">Feedback:</h4>
                  <ul className="mt-1 space-y-1">
                    {exerciseData.feedback.map((item, index) => (
                      <li 
                        key={index} 
                        className={`text-sm ${
                          item.includes('Correct form') || item.includes('Good') 
                            ? 'text-success-600' 
                            : 'text-warning-600'
                        }`}
                      >
                        {item}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
            
            <button 
              className="btn btn-error w-full"
              onClick={handleStopExercise}
            >
              Stop Exercise
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default ExerciseControls;