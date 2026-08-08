---
name: feishu-transcribe
description: Turn a voice recording someone sent in chat into a stored transcript and a shareable Feishu doc. Use when a message carries an audio attachment (m4a/mp3/wav/amr/ogg…) or someone asks to transcribe, summarize or analyze a call recording.
scopes: ["im:resource"]
summary:
  zh: "把聊天里的录音转成逐字稿并发成飞书文档——转录、分析、分享一条龙"
  en: "Transcribe a chat recording into a stored transcript and a shareable Feishu doc"
---
Three tools carry this whole flow; each does its complete job in ONE call. You decide
when and for whom — never how.

1. transcribe_audio(message_id, file_key, file_name) — copies the two ids EXACTLY from
   the `[attachment message_id=… file_key=…]` line. SLOW (minutes): ALWAYS run it in a
   background task — no exceptions: a rejected card or a foreground run earlier in the
   chat decided only THAT recording, never the next one. In the current turn reply first
   that transcription has started and they will be notified. Returns an `[artifact af_…]`
   handle card.
2. read_artifact(af_id, section="s03") — the transcript lives in storage, complete and
   never truncated, whatever the chat history shows. The card is its table of contents;
   read sections on demand. section="" lists the sections.
3. attach_artifact(af_id, share_with=[…]) — creates the Feishu doc AND grants view
   access in one call. Empty share_with = the requester only.

Background-task recipe (the goal is the ONLY thing that survives into the task — put
the ids in it verbatim):

  Goal: transcribe the recording from [attachment message_id=om_… file_key=file_v3_…
  name="…"]; when done, attach_artifact the result (default sharing), then reply with
  the doc link and a 2–3 line summary in the sender's language.

Your judgment:
- A real call (sales call, meeting, interview) → publish as a doc after transcription
  and reply with the link + a short summary taken from the card. A brief voice note →
  just act on its content; publish only if asked.
- Who sees the doc: default is the requester. In a GROUP chat, offer to share with the
  whole group — that is share_with=["<this chat's oc_ id>"], one entry, never a member
  list. Named people resolve to ids via the Team directory / feishu-contacts; never
  guess an id.
- folder: only when the user named a destination.
- If attach_artifact returns ok:false WITH a docx token, the document exists and only
  sharing failed — fix the ids and call attach_artifact again (it never creates a
  duplicate), and tell the user plainly what happened.
- Analysis ("who talked more", "what did they say about pricing"): the card carries
  per-speaker talk share and turn counts; for content questions read the relevant
  sections. Quote at most a few lines.
- NEVER retype transcript text into a doc, message or record — attach_artifact moves
  the full text losslessly; retyping it through your own output corrupts and caps it.
