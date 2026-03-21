import { apiClient } from './apiClient';
import type {
  Session,
  SessionCreate,
  SessionAutosave,
  SessionCheckResponse,
  SessionSubmitResponse,
  SessionResponse,
  Problem,
  ProblemsListResponse,
  Submission,
  SubmissionCreate,
  SubmissionsListResponse,
} from '../types/api';

// ============================================
// SESSION API
// ============================================

/**
 * Create a new session or resume an active session for a problem
 */
export const createSession = async (data: SessionCreate): Promise<SessionResponse> => {
  return apiClient.post<SessionResponse>('/sessions/', data);
};

/**
 * Get a specific session by ID
 */
export const getSession = async (sessionId: string): Promise<SessionResponse> => {
  return apiClient.get<SessionResponse>(`/sessions/${sessionId}`);
};

/**
 * Get the active session for a specific problem
 */
export const getActiveSession = async (problemId: string): Promise<SessionResponse> => {
  return apiClient.get<SessionResponse>(`/sessions/problem/${problemId}/active`);
};

/**
 * Auto-save session data (called every 10 seconds)
 */
export const autosaveSession = async (
  sessionId: string,
  data: SessionAutosave
): Promise<SessionResponse> => {
  return apiClient.put<SessionResponse>(`/sessions/${sessionId}/autosave`, data);
};

/**
 * Pause a session
 */
export const pauseSession = async (sessionId: string): Promise<SessionResponse> => {
  return apiClient.put<SessionResponse>(`/sessions/${sessionId}/pause`, {});
};

/**
 * Resume a paused session
 */
export const resumeSession = async (sessionId: string): Promise<SessionResponse> => {
  return apiClient.put<SessionResponse>(`/sessions/${sessionId}/resume`, {});
};

/**
 * Get AI feedback on current solution (Check button)
 */
export const checkSession = async (sessionId: string): Promise<SessionCheckResponse> => {
  return apiClient.post<SessionCheckResponse>(`/sessions/${sessionId}/check`, {});
};

/**
 * Submit solution for final evaluation (Submit button)
 */
export const submitSession = async (sessionId: string): Promise<SessionSubmitResponse> => {
  return apiClient.post<SessionSubmitResponse>(`/sessions/${sessionId}/submit`, {});
};

/**
 * Get all submissions for a specific problem
 */
export const getProblemSubmissions = async (problemId: string): Promise<any[]> => {
  return apiClient.get<any[]>(`/sessions/problem/${problemId}/submissions`);
};

/**
 * Stream chat with AI bot (chat history managed on backend)
 */
export const streamChat = async (
  sessionId: string,
  message: string,
  diagramData: any
): Promise<Response> => {
  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
  const accessToken = localStorage.getItem('access_token');
  
  const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}/ai-chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${accessToken}`
    },
    body: JSON.stringify({
      message,
      diagram_data: diagramData || {}
    })
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Failed to get AI response: ${response.status} - ${errorText}`);
  }

  return response;
};

/**
 * Stream submission evaluation with SSE (progressive results)
 */
export const streamSubmit = async (
  sessionId: string
): Promise<Response> => {
  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
  const accessToken = localStorage.getItem('access_token');
  
  const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}/submit-stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${accessToken}`
    }
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Failed to submit: ${response.status} - ${errorText}`);
  }

  return response;
};

/**
 * Abandon a session (user wants to start fresh)
 */
export const abandonSession = async (sessionId: string): Promise<void> => {
  return apiClient.delete<void>(`/sessions/${sessionId}`);
};

/**
 * Get all sessions for the current user
 */
export const getMySessions = async (skip = 0, limit = 100): Promise<Session[]> => {
  return apiClient.get<Session[]>(`/sessions/user/my-sessions?skip=${skip}&limit=${limit}`);
};

/**
 * Extract Excalidraw data from session (for debugging)
 */
export const extractSessionData = async (sessionId: string): Promise<any> => {
  return apiClient.get<any>(`/sessions/${sessionId}/extract`);
};

// ============================================
// PROBLEM API
// ============================================

/**
 * Get all problems with pagination
 */
export const getProblems = async (
  skip = 0,
  limit = 50,
  difficulty?: string,
  category?: string
): Promise<ProblemsListResponse> => {
  let url = `/problems/?skip=${skip}&limit=${limit}`;
  if (difficulty) url += `&difficulty=${difficulty}`;
  if (category) url += `&category=${category}`;
  return apiClient.get<ProblemsListResponse>(url);
};

/**
 * Get a specific problem by ID
 */
export const getProblem = async (problemId: string): Promise<Problem> => {
  return apiClient.get<Problem>(`/problems/${problemId}`);
};

// ============================================
// SUBMISSION API
// ============================================

/**
 * Create submission from session
 */
export const createSubmissionFromSession = async (
  sessionId: string
): Promise<Submission> => {
  return apiClient.post<Submission>(`/submissions/from-session/${sessionId}`, {});
};

/**
 * Get all submissions for the current user
 */
export const getMySubmissions = async (skip = 0, limit = 100): Promise<SubmissionsListResponse> => {
  return apiClient.get<SubmissionsListResponse>(`/submissions/user/my-submissions?skip=${skip}&limit=${limit}`);
};

/**
 * Get a specific submission by ID
 */
export const getSubmission = async (submissionId: string): Promise<Submission> => {
  return apiClient.get<Submission>(`/submissions/${submissionId}`);
};
