import React, { useState, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { WorkoutContext } from '../context/WorkoutContext';

const Survey = () => {
  const { generateWorkoutPlan, loading, error } = useContext(WorkoutContext);
  const navigate = useNavigate();
  
  // Survey form state
  const [formData, setFormData] = useState({
    weight: '',
    height: '',
    gender: '',
    activity: '',
    goal: '',
    intensity: ''
  });
  
  // Track current step in multi-step form
  const [currentStep, setCurrentStep] = useState(1);
  const totalSteps = 3;
  
  // Progress percentage
  const progress = ((currentStep - 1) / totalSteps) * 100;
  
  // Handle form input changes
  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prevData => ({
      ...prevData,
      [name]: value
    }));
  };
  
  // Go to next step
  const handleNextStep = () => {
    setCurrentStep(prevStep => prevStep + 1);
  };
  
  // Go to previous step
  const handlePrevStep = () => {
    setCurrentStep(prevStep => prevStep - 1);
  };
  
  // Handle form submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    try {
      const workoutPlan = await generateWorkoutPlan(formData);
      
      if (workoutPlan) {
        navigate('/workout');
      }
    } catch (err) {
      console.error('Error submitting survey:', err);
    }
  };
  
  // Validate current step
  const validateCurrentStep = () => {
    if (currentStep === 1) {
      return formData.weight && formData.height && formData.gender;
    } else if (currentStep === 2) {
      return formData.activity;
    } else if (currentStep === 3) {
      return formData.goal && formData.intensity;
    }
    return false;
  };
  
  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Fitness Survey</h1>
      
      {/* Progress bar */}
      <div className="w-full bg-gray-200 rounded-full h-2.5 mb-6">
        <div 
          className="bg-primary-600 h-2.5 rounded-full transition-all duration-500"
          style={{ width: `${progress}%` }}
        ></div>
      </div>
      
      <div className="card">
        <h2 className="text-xl font-bold mb-6">
          {currentStep === 1 && "Basic Information"}
          {currentStep === 2 && "Current Activity Level"}
          {currentStep === 3 && "Fitness Goals"}
        </h2>
        
        <form onSubmit={handleSubmit}>
          {/* Step 1: Basic Information */}
          {currentStep === 1 && (
            <div className="space-y-4">
              <div>
                <label htmlFor="weight" className="form-label">Weight (kg)</label>
                <input
                  type="number"
                  id="weight"
                  name="weight"
                  className="form-input"
                  placeholder="Enter your weight in kg"
                  value={formData.weight}
                  onChange={handleChange}
                  required
                />
              </div>
              
              <div>
                <label htmlFor="height" className="form-label">Height (cm)</label>
                <input
                  type="number"
                  id="height"
                  name="height"
                  className="form-input"
                  placeholder="Enter your height in cm"
                  value={formData.height}
                  onChange={handleChange}
                  required
                />
              </div>
              
              <div>
                <label className="form-label">Gender</label>
                <div className="mt-1 space-x-4">
                  <label className="inline-flex items-center">
                    <input
                      type="radio"
                      name="gender"
                      value="male"
                      className="form-radio"
                      checked={formData.gender === 'male'}
                      onChange={handleChange}
                    />
                    <span className="ml-2">Male</span>
                  </label>
                  
                  <label className="inline-flex items-center">
                    <input
                      type="radio"
                      name="gender"
                      value="female"
                      className="form-radio"
                      checked={formData.gender === 'female'}
                      onChange={handleChange}
                    />
                    <span className="ml-2">Female</span>
                  </label>
                  
                  <label className="inline-flex items-center">
                    <input
                      type="radio"
                      name="gender"
                      value="other"
                      className="form-radio"
                      checked={formData.gender === 'other'}
                      onChange={handleChange}
                    />
                    <span className="ml-2">Other</span>
                  </label>
                </div>
              </div>
            </div>
          )}
          
          {/* Step 2: Activity Level */}
          {currentStep === 2 && (
            <div className="space-y-4">
              <p className="mb-4 text-gray-600">How would you describe your current activity level?</p>
              
              <div className="space-y-2">
                <label className="block p-4 border rounded-lg hover:bg-gray-50 cursor-pointer">
                  <input
                    type="radio"
                    name="activity"
                    value="sedentary"
                    className="form-radio"
                    checked={formData.activity === 'sedentary'}
                    onChange={handleChange}
                  />
                  <span className="ml-2 font-medium">Sedentary</span>
                  <p className="mt-1 text-sm text-gray-500 ml-6">Little to no regular physical activity</p>
                </label>
                
                <label className="block p-4 border rounded-lg hover:bg-gray-50 cursor-pointer">
                  <input
                    type="radio"
                    name="activity"
                    value="lightly active"
                    className="form-radio"
                    checked={formData.activity === 'lightly active'}
                    onChange={handleChange}
                  />
                  <span className="ml-2 font-medium">Lightly Active</span>
                  <p className="mt-1 text-sm text-gray-500 ml-6">Light exercise 1-3 days per week</p>
                </label>
                
                <label className="block p-4 border rounded-lg hover:bg-gray-50 cursor-pointer">
                  <input
                    type="radio"
                    name="activity"
                    value="moderately active"
                    className="form-radio"
                    checked={formData.activity === 'moderately active'}
                    onChange={handleChange}
                  />
                  <span className="ml-2 font-medium">Moderately Active</span>
                  <p className="mt-1 text-sm text-gray-500 ml-6">Moderate exercise 3-5 days per week</p>
                </label>
                
                <label className="block p-4 border rounded-lg hover:bg-gray-50 cursor-pointer">
                  <input
                    type="radio"
                    name="activity"
                    value="very active"
                    className="form-radio"
                    checked={formData.activity === 'very active'}
                    onChange={handleChange}
                  />
                  <span className="ml-2 font-medium">Very Active</span>
                  <p className="mt-1 text-sm text-gray-500 ml-6">Hard exercise 6-7 days per week</p>
                </label>
                
                <label className="block p-4 border rounded-lg hover:bg-gray-50 cursor-pointer">
                  <input
                    type="radio"
                    name="activity"
                    value="extra active"
                    className="form-radio"
                    checked={formData.activity === 'extra active'}
                    onChange={handleChange}
                  />
                  <span className="ml-2 font-medium">Extra Active</span>
                  <p className="mt-1 text-sm text-gray-500 ml-6">Very hard exercise, physical job or training twice a day</p>
                </label>
              </div>
            </div>
          )}
          
          {/* Step 3: Fitness Goals */}
          {currentStep === 3 && (
            <div className="space-y-6">
              <div>
                <label className="form-label">What is your primary fitness goal?</label>
                <select
                  name="goal"
                  className="form-select mt-1"
                  value={formData.goal}
                  onChange={handleChange}
                  required
                >
                  <option value="">Select a goal</option>
                  <option value="weight loss">Weight Loss</option>
                  <option value="muscle gain">Muscle Gain</option>
                  <option value="improve strength">Improve Strength</option>
                  <option value="improve endurance">Improve Endurance</option>
                  <option value="improve flexibility">Improve Flexibility</option>
                  <option value="general fitness">General Fitness</option>
                </select>
              </div>
              
              <div>
                <label className="form-label">How much time can you spend working out each week?</label>
                <select
                  name="intensity"
                  className="form-select mt-1"
                  value={formData.intensity}
                  onChange={handleChange}
                  required
                >
                  <option value="">Select an option</option>
                  <option value="minimal (1-2 hours/week)">Minimal (1-2 hours/week)</option>
                  <option value="moderate (3-4 hours/week)">Moderate (3-4 hours/week)</option>
                  <option value="high (5-7 hours/week)">High (5-7 hours/week)</option>
                  <option value="very high (8+ hours/week)">Very High (8+ hours/week)</option>
                </select>
              </div>
            </div>
          )}
          
          {/* Error message */}
          {error && (
            <div className="mt-4 p-3 bg-error-100 text-error-700 rounded-md">
              {error}
            </div>
          )}
          
          {/* Navigation buttons */}
          <div className="flex justify-between mt-8">
            {currentStep > 1 ? (
              <button
                type="button"
                className="btn btn-outline"
                onClick={handlePrevStep}
              >
                Previous
              </button>
            ) : (
              <div></div> // Empty div to maintain layout
            )}
            
            {currentStep < totalSteps ? (
              <button
                type="button"
                className="btn btn-primary"
                onClick={handleNextStep}
                disabled={!validateCurrentStep()}
              >
                Next
              </button>
            ) : (
              <button
                type="submit"
                className="btn btn-primary"
                disabled={loading || !validateCurrentStep()}
              >
                {loading ? (
                  <span className="flex items-center">
                    <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Generating Plan...
                  </span>
                ) : (
                  'Generate Workout Plan'
                )}
              </button>
            )}
          </div>
        </form>
      </div>
    </div>
  );
};

export default Survey;