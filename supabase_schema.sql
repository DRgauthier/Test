-- Supabase SQL Schema for Crossword Game

-- 1. Create lobbies table
CREATE TABLE lobbies (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    host_id UUID NOT NULL REFERENCES auth.users(id),
    guest_id UUID REFERENCES auth.users(id),
    status TEXT NOT NULL DEFAULT 'waiting', -- 'waiting', 'playing', 'finished'
    game_state JSONB DEFAULT '{}'::jsonb
);

-- 2. Enable Row Level Security (RLS)
ALTER TABLE lobbies ENABLE ROW LEVEL SECURITY;

-- 3. Create Policies

-- Allow anyone authenticated to view all lobbies (so they can find one to join)
CREATE POLICY "Anyone can view lobbies"
ON lobbies FOR SELECT
TO authenticated
USING (true);

-- Allow authenticated users to create a lobby
CREATE POLICY "Users can create lobbies"
ON lobbies FOR INSERT
TO authenticated
WITH CHECK (auth.uid() = host_id);

-- Allow participants (host or guest) to update the lobby (e.g. game state, joining)
CREATE POLICY "Participants can update lobbies"
ON lobbies FOR UPDATE
TO authenticated
USING (auth.uid() = host_id OR auth.uid() = guest_id OR guest_id IS NULL);

-- 4. Enable Realtime for lobbies
-- Note: You may also need to configure this in the Supabase Dashboard UI (Database -> Publications)
-- but this SQL will add the table to the default 'supabase_realtime' publication.
BEGIN;
  DROP PUBLICATION IF EXISTS supabase_realtime;
  CREATE PUBLICATION supabase_realtime;
COMMIT;
ALTER PUBLICATION supabase_realtime ADD TABLE lobbies;

-- (Optional) If you want to use Presence or Broadcast without listening to a specific table,
-- that is handled purely on the client-side, but game state sync will be done via table updates
-- so we need Realtime on the `lobbies` table.
