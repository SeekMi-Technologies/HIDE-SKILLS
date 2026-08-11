---
name: feishu-transcribe
description: Turn a voice recording into a stored transcript and a shareable Feishu doc. Use when a message carries an audio attachment (m4a/mp3/wav/amr/ogg…), when a recording link needs transcribing (a URL in a base row, a hosted audio file), or when someone asks to transcribe, summarize or analyze a call recording.
scopes: ["im:resource"]
summary:
  zh: "把聊天录音或录音链接转成逐字稿并发成飞书文档——转录、分析、分享一条龙"
  en: "Transcribe a chat recording or a recording link into a stored transcript and a shareable Feishu doc"
---
Three tools carry this whole flow; each does its complete job in ONE call. You decide
when and for whom — never how.

1. Getting the transcript — pick the tool by where the audio IS:
   - transcribe_audio(message_id, file_key, file_name) — it arrived as a chat
     attachment. Copy the two ids EXACTLY from the `[attachment message_id=…
     file_key=…]` line. Every call pays for the audio again: call it ONCE.
   - transcribe_url(source_url) — it is a link (a URL in a base row, a hosted
     recording). Paste the https URL whole, exactly as written. Never check whether a
     link was transcribed before; the tool answers that itself. Say a transcript was
     re-used, or that nothing was paid for, ONLY when its reply said so.
   Both are SLOW (minutes): ALWAYS run them in a background task — no exceptions: a
   rejected card or a foreground run earlier in the chat decided only THAT recording,
   never the next one. In the current turn reply first that transcription has started
   and they will be notified. Both return an `[artifact af_…]` handle card.
2. read_artifact(af_id, section="s03") — the transcript lives in storage, complete and
   never truncated, whatever the chat history shows. The card is its table of contents;
   read sections on demand. section="" lists the sections.
3. attach_artifact(af_id, share_with=[…]) — creates the Feishu doc AND grants view
   access in one call. Empty share_with = the requester only.

Background-task recipe (the goal is the ONLY thing that survives into the task — put
the ids or the link in it verbatim):

  Goal: transcribe the recording from [attachment message_id=om_… file_key=file_v3_…
  name="…"]; when done, attach_artifact the result (default sharing), then reply with
  the doc link and a 2–3 line summary in the sender's language.

  Goal: transcribe the recording at https://…/audio/….m4a; when done, attach_artifact
  the result (default sharing), then reply with the doc link and a 2–3 line summary in
  the sender's language.

Your judgment:
- A real call (sales call, meeting, interview) → publish as a doc after transcription
  and reply with the link + a short summary taken from the card. A brief voice note →
  just act on its content; publish only if asked.
- Several recordings at once (a base view, a row range): read the rows first, then put
  every link in ONE goal, verbatim, and say what to do with each result. Never invent
  or complete a URL — a link you did not read from a record does not exist.
- Who sees the doc: default is the requester. In a GROUP chat, offer to share with the
  whole group — that is share_with=["<this chat's oc_ id>"], one entry, never a member
  list. Named people resolve to ids via the Team directory / feishu-contacts; never
  guess an id.
- folder: only when the user named a destination.
- If attach_artifact returns ok:false WITH a docx token, the document exists and only
  sharing failed — fix the ids and call attach_artifact again (it never creates a
  duplicate), and tell the user plainly what happened.
- If transcribe_url reports the link could not be downloaded, it is not publicly
  reachable: say so and ask for the recording as a chat attachment instead. Do not
  retry the same link and do not try to fetch it another way.
- Analysis ("who talked more", "what did they say about pricing"): the card carries
  per-speaker talk share and turn counts; for content questions read the relevant
  sections. Quote at most a few lines.
- NEVER retype transcript text into a doc, message or record — attach_artifact moves
  the full text losslessly; retyping it through your own output corrupts and caps it.
