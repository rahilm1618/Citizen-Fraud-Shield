import { useState, useEffect, useRef, useCallback } from 'react';
import { createLiveSession, sendAudioChunk, finalizeLiveSession } from '../lib/api';

export function useAudioCapture(onScoreUpdate: (data: any) => void) {
  const [isRecording, setIsRecording] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const sessionIdRef = useRef<string | null>(null);
  
  const streamRef = useRef<MediaStream | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunkQueueRef = useRef<Blob[]>([]);
  const isProcessingRef = useRef(false);
  const stopRequestedRef = useRef(false);
  const recordingTimerRef = useRef<number | null>(null);

  // Process the queue sequentially
  const processQueue = useCallback(async () => {
    if (isProcessingRef.current || chunkQueueRef.current.length === 0) return;
    
    // We need a session ID to send chunks
    if (!sessionIdRef.current) {
      if (!isProcessingRef.current) {
        isProcessingRef.current = true;
        try {
          const session = await createLiveSession();
          sessionIdRef.current = session.id;
        } catch (err) {
          setError("Failed to create live session");
          stopRecording();
        } finally {
          isProcessingRef.current = false;
          // After session creation, try processing again
          setTimeout(processQueue, 0); 
        }
      }
      return;
    }

    isProcessingRef.current = true;
    const currentChunk = chunkQueueRef.current.shift();
    
    if (currentChunk) {
      try {
        const response = await sendAudioChunk(sessionIdRef.current, currentChunk);
        onScoreUpdate(response);
      } catch (err) {
        console.error("Failed to process audio chunk:", err);
      }
    }
    
    isProcessingRef.current = false;
    
    // If more items in queue, continue processing
    if (chunkQueueRef.current.length > 0) {
      setTimeout(processQueue, 0);
    } else if (stopRequestedRef.current) {
      // If we've processed everything and stop was requested, clean up session
      if (sessionIdRef.current) {
        try {
          const finalSession = await finalizeLiveSession(sessionIdRef.current);
          onScoreUpdate(finalSession);
        } catch (err) {
          console.error("Failed to finalize session:", err);
        }
      }
      setIsRecording(false);
    }
  }, [onScoreUpdate]);

  const startNewRecorder = useCallback(() => {
    if (!streamRef.current || stopRequestedRef.current) return;
    
    const mediaRecorder = new MediaRecorder(streamRef.current);
    recorderRef.current = mediaRecorder;
    
    let audioChunks: BlobPart[] = [];
    
    mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        audioChunks.push(event.data);
      }
    };
    
    mediaRecorder.onstop = () => {
      if (audioChunks.length > 0) {
        const blob = new Blob(audioChunks, { type: 'audio/webm' });
        chunkQueueRef.current.push(blob);
        processQueue();
      }
      // Instantly start the next one if not stopped
      if (!stopRequestedRef.current) {
        startNewRecorder();
      }
    };
    
    mediaRecorder.start();
    
    // Record for 8 seconds, then stop (which triggers the next one)
    recordingTimerRef.current = window.setTimeout(() => {
      if (mediaRecorder.state === 'recording') {
        mediaRecorder.stop();
      }
    }, 8000);
    
  }, [processQueue]);

  const startRecording = useCallback(async () => {
    setError(null);
    stopRequestedRef.current = false;
    chunkQueueRef.current = [];
    sessionIdRef.current = null;
    
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      setIsRecording(true);
      startNewRecorder();
    } catch (err: any) {
      console.error('Error accessing microphone:', err);
      setError('Microphone permission denied. Please allow microphone access to use live tracking.');
      setIsRecording(false);
    }
  }, [startNewRecorder]);

  const stopRecording = useCallback(() => {
    stopRequestedRef.current = true;
    
    if (recordingTimerRef.current) {
      clearTimeout(recordingTimerRef.current);
    }
    
    if (recorderRef.current && recorderRef.current.state === 'recording') {
      recorderRef.current.stop();
    }
    
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    
    // Note: We don't set isRecording(false) here, we wait for the queue to finish processing
    if (chunkQueueRef.current.length === 0 && !isProcessingRef.current) {
        setIsRecording(false);
    }
  }, []);
  
  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopRequestedRef.current = true;
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
    };
  }, []);

  return {
    isRecording,
    error,
    startRecording,
    stopRecording
  };
}
