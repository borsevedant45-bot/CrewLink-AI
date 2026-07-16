export interface Incident {
  id: string;
  zone_id: string;
  category: string;
  description: string;
  priority_score: number;
  status: string;
  source: string;
  created_at: string;
}

export interface CrowdDensityReading {
  id: string;
  zone_id: string;
  occupancy: number;
  capacity: number;
  density_level: string;
  recorded_at: string;
}

export interface VolunteerPositionPing {
  id: string;
  volunteer_id: string;
  zone_id: string;
  recorded_at: string;
}

export interface ChatMessage {
  id: string;
  session_id: string;
  sender_type: string;
  content: string;
  translated_content: string | null;
  original_language: string;
  created_at: string;
}

export interface Zone {
  id: string;
  name: string;
  capacity: number;
}

export interface CursorPage<T> {
  data: T[];
  pagination: {
    next_cursor: string | null;
    has_more: boolean;
  };
}

export type ConnectionStatus = 'connecting' | 'connected' | 'polling' | 'error';

export interface WsEvent {
  event: string;
  data: Record<string, unknown>;
  emitted_at: string;
}
