"""Quick test for OpenAI-compatible LLM (e.g. Ollama via ngrok).

To point the livsyt-ai-4 app to this same endpoint, set in .env:
  LLM_BASE_URL=https://artful-microchemical-madie.ngrok-free.dev/v1
  LLM_API_KEY=ollama
  MODEL_STRING=qwen2.5:14b
"""
from openai import OpenAI

client = OpenAI(
    base_url="https://artful-microchemical-madie.ngrok-free.dev/v1",
    api_key="ollama",
)

stream = client.chat.completions.create(
    model="deepseek-r1:latest",
    messages=[
        {"role": "user", "content": '''
            }
[ '9:00-18:00' ]
1 2026-02-27T12:30:00.000Z
1.1 2026-02-27T12:30:00.000Z
1.2 2026-02-27T12:30:00.000Z
2 2026-02-27T12:30:00.000Z
2.1 2026-02-27T12:30:00.000Z
3 2026-02-27T12:30:00.000Z
3.1 2026-02-27T12:30:00.000Z
4 2026-02-27T12:30:00.000Z
4.1 2026-02-27T12:30:00.000Z
Error updating tasks: PrismaClientKnownRequestError: 
Invalid `prisma.$executeRawUnsafe()` invocation:


Raw query failed. Code: `42883`. Message: `db error: ERROR: function hstore(tasks) does not exist
HINT: No function matches the given name and argument types. You might need to add explicit type casts.`
    at Rn.handleRequestError (/Users/__deesh_reddy__/projects/gantt-backend/node_modules/@prisma/client/runtime/library.js:174:7325)
    at Rn.handleAndLogRequestError (/Users/__deesh_reddy__/projects/gantt-backend/node_modules/@prisma/client/runtime/library.js:174:6754)
    at Rn.request (/Users/__deesh_reddy__/projects/gantt-backend/node_modules/@prisma/client/runtime/library.js:174:6344)
    at saveTaskToDB (/Users/__deesh_reddy__/projects/gantt-backend/src/services/autoschedule.ts:425:9)
    at Hn.onAfterAutoSchedule (/Users/__deesh_reddy__/projects/gantt-backend/src/services/autoschedule.ts:126:9) {
  code: 'P2010',
  clientVersion: '4.16.2',
  meta: {
    code: '42883',
    message: 'db error: ERROR: function hstore(tasks) does not exist\n' +
      'HINT: No function matches the given name and argument types. You might need to add explicit type casts.'
  }
}
[09:24:55 UTC] INFO: request completed
    reqId: "req-1"
    res: {
      "statusCode": 200
    }
    responseTime: 1148.329415999353
^Csecond SIGINT, exiting
❯ 
❯ 
❯ 
❯ 
        -- Workaround for hstore(tasks) trigger error when app user cannot replace production.log_history.
-- This function runs the batch schedule update with log_history trigger disabled, so gantt-backend
-- can succeed without requiring the log_history fix to be applied (or when fix cannot be applied).
-- Run with migration user (e.g. postgres / table owner) so DISABLE/ENABLE TRIGGER works.

CREATE OR REPLACE FUNCTION production.batch_update_task_schedule(
  p_ids uuid[],
  p_projected_starts timestamptz[],
  p_projected_ends timestamptz[],
  p_delays int[],
  p_durations int[]
)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = production
AS $$
BEGIN
  ALTER TABLE production.tasks DISABLE TRIGGER log_history_tasks_trigger;

  UPDATE production.tasks t
  SET
    projected_start = u.projected_start,
    projected_end = u.projected_end,
    delay = u.delay,
    duration = u.duration
  FROM (
    SELECT
      unnest(p_ids) AS id,
      unnest(p_projected_starts) AS projected_start,
      unnest(p_projected_ends) AS projected_end,
      unnest(p_delays) AS delay,
      unnest(p_durations) AS duration
  ) AS u
  WHERE t.id = u.id;

  ALTER TABLE production.tasks ENABLE TRIGGER log_history_tasks_trigger;
END;
$$;

COMMENT ON FUNCTION production.batch_update_task_schedule(uuid[], timestamptz[], timestamptz[], int[], int[]) IS
  'Batch update task schedule fields; used by gantt-backend autoschedule when log_history trigger would fail (hstore/tasks).';
 
 analyse this error and provide a solution to fix it
        '''}
    ],
    stream=True,
)

for chunk in stream:
    if chunk.choices[0].delta.content is not None:
        print(chunk.choices[0].delta.content, end="")
print()