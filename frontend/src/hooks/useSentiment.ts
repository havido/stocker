import { useState, useCallback } from 'react';

interface SentimentResult {
  status: 'processing' | 'completed' | 'error';
  task_id?: string;
  result?: any;
}

export function useSentiment() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SentimentResult | null>(null);

  const pollStatus = useCallback(async (taskId: string) => {
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`/api/status/${taskId}`);
        const data = await res.json();
        
        if (data.status === 'completed') {
          setResult({ status: 'completed', result: data.result });
          clearInterval(interval);
          setLoading(false);
        }
      } catch (err) {
        console.error("Polling error", err);
        clearInterval(interval);
        setResult({ status: 'error' });
        setLoading(false);
      }
    }, 2000); // poll every 2 seconds
  }, []);

  const analyzeTicker = useCallback(async (ticker: string) => {
    setLoading(true);
    setResult(null);
    try {
      const res = await fetch('/api/ticker', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticker })
      });
      const data = await res.json();
      
      if (data.status === 'hit') {
        setResult({ status: 'completed', result: data.data });
        setLoading(false);
      } else if (data.task_id) {
        setResult({ status: 'processing', task_id: data.task_id });
        pollStatus(data.task_id);
      }
    } catch (err) {
      console.error("Analysis error", err);
      setResult({ status: 'error' });
      setLoading(false);
    }
  }, [pollStatus]);

  return { analyzeTicker, loading, result };
}
