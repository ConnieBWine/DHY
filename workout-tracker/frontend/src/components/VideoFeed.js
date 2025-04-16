import React, { useRef, useState, useEffect, useCallback } from 'react';
import Webcam from 'react-webcam';

// VideoFeed component for workout tracking with WebSocket connection
const VideoFeed = ({ 
  onExerciseData, 
  active = true,
  selectedExercise = null,
  className = ''
}) => {
  // Refs
  const webcamRef = useRef(null);
  const canvasRef = useRef(null);
  const wsRef = useRef(null);
  
  // State
  const [isConnected, setIsConnected] = useState(false);
  const [isCameraReady, setIsCameraReady] = useState(false);
  const [error, setError] = useState(null);
  const [frameRate, setFrameRate] = useState(0);
  const [lastFrameTime, setLastFrameTime] = useState(0);
  const [frameCount, setFrameCount] = useState(0);

  // Video constraints
  const videoConstraints = {
    width: 640,
    height: 480,
    facingMode: "user"
  };

  // Connect to WebSocket
  const connectWebSocket = useCallback(() => {
    // Close existing connection if any
    if (wsRef.current) {
      wsRef.current.close();
    }
    
    // Create new WebSocket connection
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `ws://localhost:8000/ws/video`;
    
    wsRef.current = new WebSocket(wsUrl);
    
    // WebSocket event handlers
    wsRef.current.onopen = () => {
      console.log('WebSocket connected');
      setIsConnected(true);
      setError(null);
    };
    
    wsRef.current.onclose = (event) => {
      console.log('WebSocket disconnected', event);
      setIsConnected(false);
      
      // Try to reconnect after 2 seconds
      setTimeout(() => {
        if (active) {
          connectWebSocket();
        }
      }, 2000);
    };
    
    wsRef.current.onerror = (error) => {
      console.error('WebSocket error:', error);
      setError('Connection error. Trying to reconnect...');
    };
    
    wsRef.current.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        // Update canvas with processed image if available
        if (data.image) {
          const image = new Image();
          image.onload = () => {
            if (canvasRef.current) {
              const ctx = canvasRef.current.getContext('2d');
              ctx.drawImage(image, 0, 0, canvasRef.current.width, canvasRef.current.height);
            }
          };
          image.src = data.image;
        }
        
        // Pass exercise data to parent component
        if (data.exerciseData) {
          onExerciseData(data.exerciseData);
        }
        
        // Handle errors
        if (data.error) {
          console.error('Error from server:', data.error);
          setError(data.error);
        }
        
        // Update frame rate calculation
        const now = performance.now();
        if (lastFrameTime) {
          const deltaTime = now - lastFrameTime;
          if (deltaTime > 0) {
            // Update rolling average framerate
            const instantFps = 1000 / deltaTime;
            setFrameRate(prevFps => {
              return prevFps * 0.9 + instantFps * 0.1; // Weighted average
            });
          }
        }
        setLastFrameTime(now);
        setFrameCount(count => count + 1);
        
        // Request next frame if connected and active
        if (isConnected && active) {
          captureAndSendFrame();
        }
      } catch (err) {
        console.error('Error parsing WebSocket message:', err);
      }
    };
    
  }, [active, lastFrameTime, onExerciseData]);

  // Capture and send frame to server
  const captureAndSendFrame = useCallback(() => {
    if (webcamRef.current && wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      try {
        // Get webcam image
        const imageSrc = webcamRef.current.getScreenshot();
        
        if (!imageSrc) return;
        
        // Create message with image data and current exercise
        const message = {
          image: imageSrc
        };
        
        // Add exercise info if available
        if (selectedExercise) {
          message.exercise = selectedExercise;
        }
        
        // Send to server
        wsRef.current.send(JSON.stringify(message));
      } catch (err) {
        console.error('Error capturing or sending frame:', err);
      }
    }
  }, [selectedExercise]);

  // Initialize WebSocket connection
  useEffect(() => {
    if (active && isCameraReady) {
      connectWebSocket();
    }
    
    return () => {
      // Clean up WebSocket connection
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [active, connectWebSocket, isCameraReady]);

  // Start sending frames when connection is established
  useEffect(() => {
    if (isConnected && active && isCameraReady) {
      captureAndSendFrame();
    }
  }, [isConnected, active, isCameraReady, captureAndSendFrame]);

  // Handle webcam ready state
  const handleWebcamReady = () => {
    setIsCameraReady(true);
  };

  return (
    <div className={`relative ${className}`}>
      {/* Webcam video input (hidden, used for capture only) */}
      <div className="hidden">
        <Webcam
          ref={webcamRef}
          audio={false}
          videoConstraints={videoConstraints}
          screenshotFormat="image/jpeg"
          onUserMedia={handleWebcamReady}
          onUserMediaError={(err) => setError(`Camera error: ${err.message}`)}
        />
      </div>
      
      {/* Canvas for displaying processed video */}
      <canvas 
        ref={canvasRef}
        width={videoConstraints.width}
        height={videoConstraints.height}
        className="w-full h-auto rounded-lg shadow-lg"
      />
      
      {/* Status indicators */}
      <div className="absolute top-3 right-3 flex space-x-2">
        {/* Connection status */}
        <div className={`h-3 w-3 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}>
          {isConnected && <div className="pulse-recording h-3 w-3"></div>}
        </div>
        
        {/* Frame rate (if enabled) */}
        {active && isConnected && (
          <div className="bg-black bg-opacity-50 rounded px-2 text-xs text-white">
            {frameRate.toFixed(1)} FPS
          </div>
        )}
      </div>
      
      {/* Error display */}
      {error && (
        <div className="absolute bottom-3 left-3 right-3 bg-red-600 text-white px-3 py-2 rounded text-sm">
          {error}
        </div>
      )}
      
      {/* Camera not ready message */}
      {!isCameraReady && (
        <div className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-75 text-white rounded-lg">
          <div className="text-center">
            <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-white mx-auto mb-4"></div>
            <p>Initializing camera...</p>
          </div>
        </div>
      )}
      
      {/* Inactive overlay */}
      {!active && isCameraReady && (
        <div className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-75 text-white rounded-lg">
          <p className="text-xl font-bold">Camera paused</p>
        </div>
      )}
    </div>
  );
};

export default VideoFeed;