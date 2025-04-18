import React, { useRef, useState, useEffect, useCallback } from 'react';
import Webcam from 'react-webcam'; // Ensure react-webcam is installed

// VideoFeed component for workout tracking with WebSocket connection
const VideoFeed = ({
  onExerciseData, // Callback function to send exercise data to parent
  active = true, // Prop to control if the feed and processing should be active
  selectedExercise = null, // The name of the currently selected exercise
  className = '' // Optional additional CSS classes
}) => {
  // Refs for DOM elements and WebSocket
  const webcamRef = useRef(null); // Ref for the react-webcam component
  const canvasRef = useRef(null); // Ref for the canvas displaying processed video
  const wsRef = useRef(null); // Ref for the WebSocket connection

  // State variables
  const [isConnected, setIsConnected] = useState(false); // WebSocket connection status
  const [isCameraReady, setIsCameraReady] = useState(false); // Camera initialization status
  const [error, setError] = useState(null); // Stores error messages for display
  const [frameRate, setFrameRate] = useState(0); // Calculated frame rate
  const [lastFrameTime, setLastFrameTime] = useState(0); // Timestamp of the last frame processed

  // Video constraints for the webcam
  const videoConstraints = {
    width: 640,
    height: 480,
    facingMode: "user" // Use the front camera
  };

  // --- Frame Capture and Sending ---
  const captureAndSendFrame = useCallback(() => {
    // Check if all conditions are met to send a frame
    if (
        webcamRef.current &&
        wsRef.current &&
        wsRef.current.readyState === WebSocket.OPEN &&
        isCameraReady &&
        active
    ) {
      try {
        // Get screenshot from webcam as base64 data URI
        const imageSrc = webcamRef.current.getScreenshot();

        // Validate the captured image data
        const minLength = 100; // Heuristic: valid base64 jpeg URIs are usually longer
        const isValidDataUri = imageSrc &&
                              typeof imageSrc === 'string' &&
                              imageSrc.startsWith('data:image/jpeg;base64,') &&
                              imageSrc.length > minLength;

        if (!isValidDataUri) {
          console.warn('Invalid imageSrc captured, skipping frame send. Length:', imageSrc ? imageSrc.length : 'null');
          // Don't request next frame immediately if capture failed
          return;
        }

        // Prepare message payload
        const message = {
          image: imageSrc // Send the raw webcam frame
        };

        // Include the currently selected exercise if available
        if (selectedExercise) {
          message.exercise = selectedExercise;
        }

        // Send the data to the WebSocket server
        // console.log("Sending frame to WebSocket..."); // Uncomment for debugging
        wsRef.current.send(JSON.stringify(message));

      } catch (err) {
        console.error('Error in captureAndSendFrame:', err);
        setError(`Error capturing/sending frame: ${err.message}`);
      }
    } else {
        // Optional: Log why frame wasn't sent
        // console.log("Conditions not met for sending frame:", {
        //     hasWebcam: !!webcamRef.current,
        //     wsState: wsRef.current ? wsRef.current.readyState : 'no ws',
        //     isCamReady: isCameraReady,
        //     isActive: active
        // });
    }
  }, [selectedExercise, isCameraReady, active]); // Dependencies for sending logic


  // --- WebSocket Handling ---
  const connectWebSocket = useCallback(() => {
    // Close existing connection if it exists and is not already closed/closing
    if (wsRef.current &&
        (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING)) {
      console.log("Closing existing WebSocket connection before reconnecting.");
      wsRef.current.close();
    }

    // Construct WebSocket URL (ensure backend address/port are correct)
    const wsUrl = `ws://${window.location.hostname}:8000/ws/video`; // Use hostname dynamically
    console.log(`Attempting to connect WebSocket to ${wsUrl}`);
    setError(null); // Clear previous errors on connection attempt
    setIsConnected(false); // Assume disconnected until onopen fires

    try {
        // Create new WebSocket instance
        wsRef.current = new WebSocket(wsUrl);
    } catch (err) {
        console.error("Error creating WebSocket:", err);
        setError(`Failed to create WebSocket: ${err.message}. Check URL and server.`);
        return; // Stop if creation fails
    }


    // WebSocket event handlers
    wsRef.current.onopen = () => {
      console.log('WebSocket connected successfully');
      setIsConnected(true);
      setError(null); // Clear previous errors on successful connection
      // Send initial frame immediately after connection
      if (active && isCameraReady) {
        console.log("WebSocket open, sending initial frame.");
        captureAndSendFrame(); // Send the first frame
      } else {
         console.log("WebSocket open, but not sending initial frame (active/cameraReady false).");
      }
    };

    wsRef.current.onclose = (event) => {
      console.log(`WebSocket disconnected - Code: ${event.code}, Reason: "${event.reason}", Was Clean: ${event.wasClean}`);
      setIsConnected(false);
      // Attempt to reconnect after a delay ONLY if the component is still active and it wasn't a clean close (or specific codes)
      if (active && !event.wasClean) { // Add more specific error codes if needed (e.g., 1006 for abnormal closure)
        console.log('Attempting WebSocket reconnection in 3 seconds...');
        setTimeout(connectWebSocket, 3000); // Use the function directly
      } else {
        console.log("WebSocket closed cleanly or component inactive, no reconnection attempt.");
      }
    };

    wsRef.current.onerror = (event) => {
      // This event often precedes onclose when there's a connection issue
      console.error('WebSocket error event:', event);
      setError('WebSocket connection error. Check server and network. Attempting to reconnect...');
      // No need to manually call connectWebSocket here, onclose will handle reconnection logic if appropriate
    };

    wsRef.current.onmessage = (event) => {
      // console.log("WebSocket message received."); // Uncomment for debugging
      try {
        const data = JSON.parse(event.data);

        // Update canvas with processed image from backend
        if (data.image && canvasRef.current) {
          const image = new Image();
          image.onload = () => {
            const ctx = canvasRef.current.getContext('2d');
            if (ctx) { // Ensure context is available
              // Maintain aspect ratio if canvas/image sizes differ (optional)
              // Clear previous frame before drawing new one
              ctx.clearRect(0, 0, canvasRef.current.width, canvasRef.current.height);
              ctx.drawImage(image, 0, 0, canvasRef.current.width, canvasRef.current.height);
            } else {
                console.warn("Canvas context not available for drawing.");
            }
          };
          image.onerror = () => {
              console.error("Error loading image received from WebSocket.");
              setError("Failed to load processed image.");
          };
          image.src = data.image; // This is the processed image from the backend
        }

        // Pass exercise analysis data (feedback, reps, etc.) to parent
        if (data.exerciseData) {
          onExerciseData(data.exerciseData);
        }

        // Handle and display errors sent from the backend
        if (data.status === "error" || data.error) {
          const errorMessage = data.error || "Unknown server error";
          console.error('Error message received from server:', errorMessage);
          // Display a more user-friendly message for specific errors if needed
          if (typeof errorMessage === 'string' && errorMessage.includes('cv::imdecode_')) {
            setError('Server error processing video frame. Check data format.');
          } else {
             setError(`Server error: ${errorMessage}`);
          }
          // Consider if we should stop sending frames on server error
        } else {
          // Clear error if message is successful
          // setError(null); // Be cautious with this, might hide intermittent errors
        }

        // --- Frame Rate Calculation ---
        const now = performance.now();
        if (lastFrameTime > 0) {
          const deltaTime = now - lastFrameTime;
          if (deltaTime > 0) {
            const instantFps = 1000 / deltaTime;
            // Use a simple rolling average for smoother display
            setFrameRate(prevFps => (prevFps * 0.9 + instantFps * 0.1));
          }
        }
        setLastFrameTime(now);
        // --- End Frame Rate Calculation ---

        // Request the next frame processing by sending the current webcam frame
        // This creates a loop: send -> process -> receive -> send next
        if (isConnected && active && isCameraReady) {
          // console.log("Requesting next frame..."); // Uncomment for debugging
          captureAndSendFrame();
        }

      } catch (err) {
        console.error('Error parsing WebSocket message or drawing image:', err);
        setError('Error processing message from server.');
      }
    };

  }, [active, isCameraReady, onExerciseData, captureAndSendFrame]); // Removed isConnected, lastFrameTime as they are handled internally or via state setters


  // --- Effects ---

  // Effect to manage WebSocket connection based on 'active' and 'isCameraReady' state
  useEffect(() => {
    console.log(`Effect triggered: active=${active}, isCameraReady=${isCameraReady}`);
    if (active && isCameraReady) {
      console.log("Conditions met: Connecting WebSocket.");
      connectWebSocket(); // Connect when active and camera is ready
    } else {
      // Close connection if component becomes inactive or camera fails/not ready
      if (wsRef.current &&
          (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING)) {
        console.log("Conditions not met or changed: Closing WebSocket.");
        wsRef.current.close(1000, "Component inactive or camera not ready"); // 1000 = Normal Closure
      } else {
         console.log("Conditions not met, WebSocket already closed or null.");
      }
    }

    // Cleanup function: Close WebSocket when component unmounts or dependencies change causing closure
    return () => {
      console.log("Cleanup function running.");
      if (wsRef.current) {
        console.log("Cleaning up WebSocket connection.");
        // Ensure close is only called if not already closed or closing
        if (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING) {
            wsRef.current.close(1001, "Component unmounting"); // 1001 = Going Away
        }
        wsRef.current = null; // Clear the ref
      }
    };
  }, [active, isCameraReady, connectWebSocket]); // Re-run if active, camera readiness, or connect function changes


  // --- Webcam Event Handlers ---

  // Called when the webcam component successfully accesses the user's media
  const handleWebcamReady = useCallback(() => {
    console.log("Webcam ready (onUserMedia fired).");
    // Check if webcamRef is actually available, sometimes onUserMedia fires before ref is fully set
    if (webcamRef.current && webcamRef.current.video && webcamRef.current.video.readyState >= 2) { // HAVE_CURRENT_DATA or more
        console.log("Webcam stream seems active.");
        setIsCameraReady(true);
        setError(null); // Clear any previous errors
    } else {
        console.warn("onUserMedia fired, but webcam ref or video stream doesn't seem fully ready yet. Retrying check shortly.");
        // Optional: Add a small delay and re-check, or wait for the effect to trigger connection
        setTimeout(() => {
            if (webcamRef.current && webcamRef.current.video && webcamRef.current.video.readyState >= 2) {
                setIsCameraReady(true);
                setError(null);
            } else {
                 console.error("Webcam still not ready after delay.");
                 setError("Camera started but stream is not available.");
                 setIsCameraReady(false);
            }
        }, 500);
    }
  }, []); // Empty dependency array, this relies on webcamRef

  // Called when there's an error accessing the webcam
  const handleWebcamError = useCallback((err) => {
    console.error("Webcam Error (onUserMediaError):", err);
    // Provide more specific messages based on error name
    let message = `Camera error: ${err.name || 'Unknown Error'}.`;
    if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        message = 'Camera permission denied. Please allow camera access in browser settings.';
    } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
        message = 'No camera found. Please ensure a camera is connected and enabled.';
    } else if (err.name === 'NotReadableError' || err.name === 'TrackStartError') {
        message = 'Camera is already in use by another application or browser tab.';
    } else if (err.name === 'OverconstrainedError' || err.name === 'ConstraintNotSatisfiedError') {
        message = `Camera does not support requested settings (e.g., resolution). ${err.constraint}`;
    } else if (err.name === 'AbortError') {
        message = 'Camera access was aborted. Please try again.';
    } else if (err.message) { // Fallback to error message if name is generic
        message += ` ${err.message}`;
    }

    setError(message);
    setIsCameraReady(false); // Mark camera as not ready
    // WebSocket will be closed by the useEffect hook when isCameraReady becomes false
  }, []); // Empty dependency array


  // --- Rendering ---

  return (
    <div className={`relative ${className}`}>
      {/* Hidden Webcam component - used only for capturing frames */}
      {/* Render Webcam only when active to avoid unnecessary camera requests */}
      {active && (
        <div className="hidden">
            <Webcam
            ref={webcamRef}
            audio={false} // Audio not needed for processing
            videoConstraints={videoConstraints}
            screenshotFormat="image/jpeg" // Format expected by backend
            onUserMedia={handleWebcamReady} // Called when camera starts successfully
            onUserMediaError={handleWebcamError} // Called on camera error
            />
        </div>
      )}

      {/* Canvas to display the processed video feed received from the backend */}
      <canvas
        ref={canvasRef}
        width={videoConstraints.width}
        height={videoConstraints.height}
        className="w-full h-auto rounded-lg shadow-lg bg-gray-700 border border-gray-600" // Darker placeholder
      />

      {/* Status Indicators Overlay */}
      <div className="absolute top-3 right-3 flex space-x-2 items-center">
        {/* Connection status light */}
        <div title={isConnected ? 'Connected to server' : 'Disconnected from server'} className={`h-3 w-3 rounded-full transition-colors duration-300 ${isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`}>
        </div>

        {/* Frame rate display */}
        {active && isConnected && (
          <div className="bg-black bg-opacity-60 rounded px-2 py-0.5 text-xs text-white font-mono">
            {frameRate.toFixed(1)} FPS
          </div>
        )}
      </div>

      {/* Error Message Overlay */}
      {error && (
        <div className="absolute bottom-0 left-0 right-0 bg-red-600 bg-opacity-90 text-white px-3 py-2 text-sm z-10 shadow-md flex items-center justify-between">
          <span>{error}</span>
          {/* Optional: Add a button to dismiss or retry */}
          {/* <button onClick={() => setError(null)} className="ml-2 text-red-100 hover:text-white">&times;</button> */}
        </div>
      )}

      {/* Loading/Initializing Camera Overlay */}
      {active && !isCameraReady && !error && ( // Show only when active, not ready, and no error
        <div className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-75 text-white rounded-lg z-20">
          <div className="text-center">
            <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-white mx-auto mb-4"></div>
            <p>Initializing camera...</p>
            <p className="text-xs mt-2">(Allow camera permission if prompted)</p>
          </div>
        </div>
      )}

      {/* Paused Overlay */}
      {!active && isCameraReady && ( // Show only when inactive but camera was ready
        <div className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-75 text-white rounded-lg z-20">
          <p className="text-xl font-bold">Camera paused</p>
        </div>
      )}
    </div>
  );
};

export default VideoFeed;
