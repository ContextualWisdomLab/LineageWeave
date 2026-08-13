import { config } from "./config";

export interface PostSummary {
  post_id: string;
  post_title: string;
  voc_type_code: string;
  visibility_code: string;
  created_at: string;
}

export interface PostDetail extends PostSummary {
  post_body: string;
}

async function backendFetch<T>(path: string, accessToken: string): Promise<T> {
  const response = await fetch(`${config.backendBaseUrl}${path}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!response.ok) {
    throw new Error(`${path} -> HTTP ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function fetchPosts(accessToken: string): Promise<PostSummary[]> {
  return backendFetch<PostSummary[]>("/api/posts", accessToken);
}

export function fetchPost(accessToken: string, postId: string): Promise<PostDetail> {
  return backendFetch<PostDetail>(`/api/posts/${postId}`, accessToken);
}
