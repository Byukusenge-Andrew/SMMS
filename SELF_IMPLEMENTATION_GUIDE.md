# SMMS Self-Implementation Feature Roadmap & Technical Guide

Welcome to the **SMMS (Social Media Management System) Self-Implementation Guide**. This document details 6 production-grade features designed to extend the SMMS backend (Django REST Framework + Celery + PostgreSQL/Supabase) and frontend (Vite + React + TypeScript + Redux Toolkit).

Each feature includes database schemas, DRF views/serializers, background tasks, frontend component structure, and step-by-step execution instructions.

---

## Technical Stack Quick Reference

* **Backend**: Django 5.x, Django REST Framework, Celery + Redis/Valkey, PostgreSQL (Supabase).
* **Frontend**: React 18 (TypeScript), Redux Toolkit, Tailwind CSS, TanStack Router / React Router.
* **Storage**: Supabase Storage for media upload and asset management.

---

## 🚀 Feature 1: AI Content Assistant & Caption Generator

### 📋 Overview
An integrated AI tool that allows users to generate engaging post captions, hashtags, tone variations (Professional, Casual, Witty, Sales), and language translations using OpenAI or Anthropic API.

### 1. Backend Implementation

#### A. Database Model (`backend/apps/posts/models.py`)
Add an audit model to track AI generation history and token consumption.

```python
from django.db import models
from django.conf import settings

class AIGenerationLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ai_generations")
    prompt = models.TextField()
    platform = models.CharField(max_length=50, choices=[('twitter', 'Twitter/X'), ('facebook', 'Facebook'), ('linkedin', 'LinkedIn'), ('instagram', 'Instagram')])
    tone = models.CharField(max_length=50, default='professional')
    generated_text = models.TextField()
    tokens_used = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
```

#### B. Service Logic (`backend/apps/posts/services/ai_service.py`)
Create a helper function to interface with the AI Provider (e.g. OpenAI / Anthropic).

```python
import os
import openai

def generate_social_caption(prompt: str, platform: str, tone: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        # Fallback / Mock for local testing without API key
        return f"[{platform.upper()} - {tone.upper()}] ✨ {prompt}\n\n#SocialMedia #Automation #SMMS"
    
    client = openai.OpenAI(api_key=api_key)
    system_prompt = f"You are an expert social media manager crafting engaging posts for {platform}. Tone: {tone}. Keep length appropriate for {platform} and include 3 relevant hashtags."
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        max_tokens=300
    )
    return response.choices[0].message.content.strip()
```

#### C. API Endpoint (`backend/apps/posts/views.py`)

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from .services.ai_service import generate_social_caption
from .models import AIGenerationLog

class AICaptionGenerateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        prompt = request.data.get('prompt')
        platform = request.data.get('platform', 'twitter')
        tone = request.data.get('tone', 'professional')

        if not prompt:
            return Response({"error": "Prompt is required"}, status=status.HTTP_400_BAD_REQUEST)

        generated_caption = generate_social_caption(prompt, platform, tone)
        
        # Log generation
        AIGenerationLog.objects.create(
            user=request.user,
            prompt=prompt,
            platform=platform,
            tone=tone,
            generated_text=generated_caption
        )

        return Response({"caption": generated_caption, "platform": platform, "tone": tone})
```

#### D. URL Registration (`backend/apps/posts/urls.py`)
```python
path('ai/generate-caption/', AICaptionGenerateView.as_view(), name='ai-generate-caption'),
```

### 2. Frontend Implementation

#### React Component (`SMMS_frontend/keativ/src/components/content/AICaptionModal.tsx`)
```tsx
import React, { useState } from 'react';
import { Sparkles, Loader2, Copy, Check } from 'lucide-react';

interface AICaptionModalProps {
  onSelectCaption: (caption: string) => void;
  onClose: () => void;
}

export const AICaptionModal: React.FC<AICaptionModalProps> = ({ onSelectCaption, onClose }) => {
  const [prompt, setPrompt] = useState('');
  const [platform, setPlatform] = useState('twitter');
  const [tone, setTone] = useState('professional');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState('');
  const [copied, setCopied] = useState(false);

  const handleGenerate = async () => {
    if (!prompt.trim()) return;
    setLoading(true);
    try {
      const res = await fetch('/api/posts/ai/generate-caption/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${localStorage.getItem('token')}` },
        body: JSON.stringify({ prompt, platform, tone }),
      });
      const data = await res.json();
      setResult(data.caption);
    } catch (err) {
      console.error('Failed to generate caption', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 w-full max-w-lg shadow-2xl text-white">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-xl font-bold flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-purple-400" /> AI Caption Assistant
          </h3>
          <button onClick={onClose} className="text-slate-400 hover:text-white">✕</button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm text-slate-400 mb-1">What is your post about?</label>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="e.g. Launching our new eco-friendly water bottle with 20% discount..."
              className="w-full bg-slate-800 border border-slate-700 rounded-lg p-3 text-sm focus:outline-none focus:border-purple-500"
              rows={3}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-slate-400 mb-1">Platform</label>
              <select
                value={platform}
                onChange={(e) => setPlatform(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-sm"
              >
                <option value="twitter">Twitter / X</option>
                <option value="linkedin">LinkedIn</option>
                <option value="facebook">Facebook</option>
                <option value="instagram">Instagram</option>
              </select>
            </div>
            <div>
              <label className="block text-sm text-slate-400 mb-1">Tone</label>
              <select
                value={tone}
                onChange={(e) => setTone(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-sm"
              >
                <option value="professional">Professional</option>
                <option value="casual">Casual & Friendly</option>
                <option value="witty">Witty & Humorous</option>
                <option value="sales">Urgent / Promotional</option>
              </select>
            </div>
          </div>

          <button
            onClick={handleGenerate}
            disabled={loading || !prompt.trim()}
            className="w-full py-2.5 bg-gradient-to-r from-purple-600 to-indigo-600 rounded-lg font-medium hover:opacity-90 disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
            Generate Content
          </button>

          {result && (
            <div className="mt-4 p-4 bg-slate-800/80 border border-slate-700 rounded-lg space-y-3">
              <p className="text-sm text-slate-200 whitespace-pre-wrap">{result}</p>
              <div className="flex justify-end gap-2">
                <button
                  onClick={() => {
                    onSelectCaption(result);
                    onClose();
                  }}
                  className="px-3 py-1.5 bg-purple-600 hover:bg-purple-500 rounded text-xs font-semibold"
                >
                  Use This Caption
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
```

---

## 📅 Feature 2: Smart Posting Schedule & Optimal Time Recommender

### 📋 Overview
Calculates peak audience engagement hours based on historical post analytics (likes, retweets, comments) per platform, providing users with recommended time slots for scheduling posts.

### 1. Backend Implementation

#### A. Database Model (`backend/apps/analytics/models.py`)
```python
from django.db import models
from django.conf import settings

class OptimalPostingSlot(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="posting_slots")
    platform = models.CharField(max_length=50) # twitter, facebook, linkedin, instagram
    day_of_week = models.IntegerField() # 0 = Monday, 6 = Sunday
    hour_of_day = models.IntegerField() # 0-23
    score = models.FloatField(default=0.0) # Normalized engagement score (0-100)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'platform', 'day_of_week', 'hour_of_day')
```

#### B. Celery Computation Task (`backend/apps/analytics/tasks.py`)
```python
from celery import shared_task
from django.db.models import Avg, Sum
from apps.posts.models import Post
from .models import OptimalPostingSlot
from django.contrib.auth import get_user_model

User = get_user_model()

@shared_task
def calculate_optimal_posting_times_for_all_users():
    for user in User.objects.all():
        posts = Post.objects.filter(user=user, status='published')
        if not posts.exists():
            continue
        
        # Aggregate engagement score per (platform, day_of_week, hour_of_day)
        slots_data = {}
        for post in posts:
            if not post.published_at:
                continue
            day = post.published_at.weekday()
            hour = post.published_at.hour
            platform = post.platform
            
            # Simple engagement formula: likes + 2*comments + 3*shares
            metrics = getattr(post, 'analytics', None)
            score = 1.0
            if metrics:
                score = (metrics.likes or 0) + (metrics.comments or 0) * 2 + (metrics.shares or 0) * 3

            key = (platform, day, hour)
            slots_data[key] = slots_data.get(key, 0) + score

        # Normalize and save top slots
        max_score = max(slots_data.values()) if slots_data else 1.0
        for (platform, day, hour), total_score in slots_data.items():
            norm_score = round((total_score / max_score) * 100, 2)
            OptimalPostingSlot.objects.update_or_create(
                user=user,
                platform=platform,
                day_of_week=day,
                hour_of_day=hour,
                defaults={'score': norm_score}
            )
```

#### C. DRF View (`backend/apps/analytics/views.py`)
```python
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from .models import OptimalPostingSlot
from .serializers import OptimalPostingSlotSerializer

class OptimalPostingSlotListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OptimalPostingSlotSerializer

    def get_queryset(self):
        platform = self.request.query_params.get('platform')
        qs = OptimalPostingSlot.objects.filter(user=self.request.user)
        if platform:
            qs = qs.filter(platform=platform)
        return qs.order_by('-score')[:10] # Top 10 best times
```

---

## 📥 Feature 3: Unified Social Inbox & Auto-Responder

### 📋 Overview
Aggregates incoming messages and comments from connected platforms (Facebook Page DMs, Twitter DMs, Instagram comments) into a single unified workspace with automated rules-based responses.

### 1. Database Model (`backend/apps/messaging/models.py`)

```python
from django.db import models
from django.conf import settings

class UnifiedMessage(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="inbox_messages")
    platform = models.CharField(max_length=50) # facebook, twitter, instagram, linkedin
    external_id = models.CharField(max_length=255, unique=True)
    sender_name = models.CharField(max_length=255)
    sender_avatar = models.URLField(blank=True, null=True)
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    message_type = models.CharField(max_length=50, choices=[('dm', 'Direct Message'), ('comment', 'Comment'), ('mention', 'Mention')])
    received_at = models.DateTimeField()

    class Meta:
        ordering = ['-received_at']

class AutoReplyRule(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="auto_reply_rules")
    keyword = models.CharField(max_length=100, help_text="Trigger keyword e.g., 'pricing', 'support'")
    response_template = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

### 2. Auto-Response Engine (`backend/apps/messaging/services.py`)

```python
from .models import UnifiedMessage, AutoReplyRule

def evaluate_and_auto_reply(message: UnifiedMessage):
    """Checks message content against active auto-reply rules and queues a response."""
    rules = AutoReplyRule.objects.filter(user=message.user, is_active=True)
    content_lower = message.content.lower()
    
    for rule in rules:
        if rule.keyword.lower() in content_lower:
            # Trigger response (Call external integration service)
            send_external_reply(message.platform, message.external_id, rule.response_template)
            break

def send_external_reply(platform: str, external_msg_id: str, reply_text: str):
    # Integration dispatch logic for Meta API / Twitter API
    print(f"[AUTO-REPLY] Replying to {platform} msg {external_msg_id}: {reply_text}")
```

---

## 👥 Feature 4: Content Approval Engine & Team Workflow

### 📋 Overview
Introduces multi-stage publishing workflows (Draft -> Pending Review -> Approved / Changes Requested -> Scheduled) for agency and enterprise teams.

### 1. Update Post Model (`backend/apps/posts/models.py`)

```python
class Post(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending_review', 'Pending Review'),
        ('changes_requested', 'Changes Requested'),
        ('approved', 'Approved'),
        ('scheduled', 'Scheduled'),
        ('published', 'Published'),
        ('failed', 'Failed'),
    ]

    # Add approval workflow fields:
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="posts_to_review")
    feedback_notes = models.TextField(blank=True, null=True)
```

### 2. Approval Transition Endpoint (`backend/apps/posts/views.py`)

```python
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import viewsets, status
from .models import Post

class PostViewSet(viewsets.ModelViewSet):
    # Existing viewset logic ...

    @action(detail=True, methods=['post'], url_path='submit-for-review')
    def submit_for_review(self, request, pk=None):
        post = self.get_object()
        post.status = 'pending_review'
        post.save()
        return Response({'status': 'Post submitted for review'})

    @action(detail=True, methods=['post'], url_path='approve')
    def approve_post(self, request, pk=None):
        post = self.get_object()
        post.status = 'approved' if not post.scheduled_at else 'scheduled'
        post.reviewer = request.user
        post.feedback_notes = request.data.get('notes', '')
        post.save()
        return Response({'status': 'Post approved successfully'})

    @action(detail=True, methods=['post'], url_path='request-changes')
    def request_changes(self, request, pk=None):
        notes = request.data.get('notes')
        if not notes:
            return Response({'error': 'Notes are required when requesting changes'}, status=status.HTTP_400_BAD_REQUEST)
        
        post = self.get_object()
        post.status = 'changes_requested'
        post.feedback_notes = notes
        post.save()
        return Response({'status': 'Changes requested for post'})
```

---

## 📦 Feature 5: Bulk Content Importer (CSV / Excel)

### 📋 Overview
Allows users to upload a single CSV file containing dozens of posts with dates, captions, and platform targets, creating scheduled posts in bulk.

### 1. CSV Parsing Service (`backend/apps/posts/services/bulk_import.py`)

```python
import csv
import io
from datetime import datetime
from apps.posts.models import Post

def process_bulk_csv(user, file_obj) -> dict:
    decoded_file = file_obj.read().decode('utf-8')
    io_string = io.StringIO(decoded_file)
    reader = csv.DictReader(io_string)
    
    created_count = 0
    errors = []

    for row_idx, row in enumerate(reader, start=2):
        content = row.get('content')
        platform = row.get('platform')
        scheduled_at_str = row.get('scheduled_at')

        if not content or not platform or not scheduled_at_str:
            errors.append(f"Row {row_idx}: Missing required fields.")
            continue

        try:
            scheduled_at = datetime.fromisoformat(scheduled_at_str)
            Post.objects.create(
                user=user,
                content=content,
                platform=platform,
                scheduled_at=scheduled_at,
                status='scheduled'
            )
            created_count += 1
        except Exception as e:
            errors.append(f"Row {row_idx}: Invalid date format or creation failed ({str(e)}).")

    return {"created": created_count, "errors": errors}
```

---

## 📊 Feature 6: Competitor Benchmarking & Sentiment Tracking

### 📋 Overview
Monitors competitor profiles across platforms to benchmark engagement rate, follower growth, and post sentiment.

### 1. Database Model (`backend/apps/analytics/models.py`)

```python
class CompetitorTracker(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="competitors")
    name = models.CharField(max_length=255)
    platform = models.CharField(max_length=50) # twitter, instagram, linkedin
    handle = models.CharField(max_length=255)
    follower_count = models.IntegerField(default=0)
    avg_engagement_rate = models.FloatField(default=0.0)
    sentiment_score = models.FloatField(default=0.0) # -1.0 (Negative) to +1.0 (Positive)
    last_synced_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('user', 'platform', 'handle')
```

---

## 🛠️ Step-by-Step Self-Implementation Checklist

Follow this workflow to implement any of the features above cleanly:

### Step 1: Django Backend Setup
1. Edit the respective `models.py` file.
2. Run database migrations:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```
3. Create DRF serializers in `serializers.py` and views in `views.py`.
4. Register API endpoints in `urls.py`.
5. Test endpoints locally with Postman or `curl`.

### Step 2: Celery Background Tasks (if applicable)
1. Add task definitions in `tasks.py`.
2. Test Celery execution:
   ```bash
   celery -A social_media_manager worker --loglevel=info --pool=solo
   ```

### Step 3: React Frontend Integration
1. Define TypeScript interfaces in `src/types/`.
2. Add API call functions in `src/services/`.
3. Create UI component in `src/components/` or `src/pages/private/`.
4. Register the page route in `src/routes/`.
5. Run Vite dev server and test UI interaction:
   ```bash
   cd SMMS_frontend/keativ
   npm run dev
   ```

---
*Happy coding! Built for SMMS (Social Media Management System).*
