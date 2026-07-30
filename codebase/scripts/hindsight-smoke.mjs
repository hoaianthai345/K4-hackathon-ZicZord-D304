import { HindsightClient } from "@vectorize-io/hindsight-client";

const baseUrl = process.env.HINDSIGHT_BASE_URL ?? "http://localhost:8888";
const userId = process.env.DEMO_USER_ID ?? "U-DEMO-001";
const normalizedUserId = userId.toLowerCase().replace(/[^a-z0-9-]/g, "-");
const bankId = `vlearn-learning-memory-${normalizedUserId}`;
const userTag = `user:${userId}`;

const client = new HindsightClient({ baseUrl });

const learningMemorySchema = {
  type: "object",
  additionalProperties: false,
  required: ["candidates", "abstained_items"],
  properties: {
    candidates: {
      type: "array",
      maxItems: 3,
      items: {
        type: "object",
        additionalProperties: false,
        required: [
          "status",
          "topic",
          "reason",
          "evidence_turn_ids",
          "confidence"
        ],
        properties: {
          status: { type: "string", const: "proposed" },
          topic: { type: "string" },
          reason: { type: "string" },
          evidence_turn_ids: {
            type: "array",
            minItems: 1,
            items: { type: "string" }
          },
          confidence: {
            type: "string",
            enum: ["high", "medium", "low"]
          }
        }
      }
    },
    abstained_items: {
      type: "array",
      items: {
        type: "object",
        additionalProperties: false,
        required: ["reason"],
        properties: {
          reason: {
            type: "string",
            enum: [
              "insufficient_evidence",
              "ambiguous_topic",
              "source_unavailable"
            ]
          }
        }
      }
    }
  }
};

const evidence = [
  {
    turnId: "T-DEMO-001",
    content:
      "Học viên nói: Tôi chưa phân biệt được few-shot prompting và Chain-of-Thought.",
    timestamp: "2026-07-30T08:00:00+07:00"
  },
  {
    turnId: "T-DEMO-002",
    content:
      "Học viên yêu cầu giải thích lại few-shot bằng ví dụ dành cho sinh viên Software Engineering.",
    timestamp: "2026-07-30T08:05:00+07:00"
  }
];

async function retainSyntheticEvidence() {
  await client.createBank(bankId, {
    reflectMission:
      "Đề xuất tối đa ba chủ đề học viên có thể cần ôn. Không kết luận học viên đã hiểu hoặc chưa hiểu. Mọi đề xuất phải dùng turn ID từ evidence.",
    retainExtractionMode: "verbatim",
    enableObservations: false
  });

  for (const item of evidence) {
    await client.retain(bankId, `${item.turnId}: ${item.content}`, {
      timestamp: item.timestamp,
      context: "Synthetic VLearn learning interaction",
      documentId: `evidence:${item.turnId}`,
      tags: [userTag, "layer:evidence", "status:observed", "lesson:demo"],
      metadata: {
        source: "synthetic",
        turn_id: item.turnId,
        privacy: "no_real_user_data"
      },
      updateMode: "replace",
      async: false
    });
  }
}

async function proposeLearningMemory() {
  return client.reflect(
    bankId,
    [
      "Từ evidence của đúng học viên này, đề xuất phần có thể cần ôn.",
      "Không chấm mastery.",
      "Không dùng kiến thức ngoài evidence.",
      "Nếu không đủ chắc, thêm abstained_items thay vì đoán."
    ].join(" "),
    {
      tags: [userTag, "layer:evidence"],
      tagsMatch: "all_strict",
      responseSchema: learningMemorySchema,
      factTypes: ["world", "experience"],
      excludeMentalModels: true,
      includeFacts: true,
      includeToolCalls: true
    }
  );
}

async function retainConfirmedMemory(candidate) {
  const slug = candidate.topic
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");

  return client.retain(
    bankId,
    JSON.stringify({
      kind: "needs_review",
      status: "confirmed",
      topic: candidate.topic,
      reason: candidate.reason,
      evidence_turn_ids: candidate.evidence_turn_ids
    }),
    {
      context: "User-confirmed Learning Memory",
      documentId: `canonical:needs-review:${slug}`,
      tags: [userTag, "layer:canonical", "status:confirmed"],
      metadata: {
        confirmed_by: "demo_user",
        evidence_turn_ids: candidate.evidence_turn_ids.join(","),
        version: "1"
      },
      updateMode: "replace",
      async: false
    }
  );
}

async function main() {
  console.log(`Hindsight: ${baseUrl}`);
  console.log(`Bank: ${bankId}`);

  const version = await client.getVersion();
  console.log("Version:", version);

  await retainSyntheticEvidence();
  const reflection = await proposeLearningMemory();
  console.log("Reflection:", JSON.stringify(reflection, null, 2));

  if (process.env.CONFIRM_DEMO_MEMORY === "1") {
    const structured =
      reflection.structured_output ?? reflection.structuredOutput ?? null;
    const firstCandidate = structured?.candidates?.[0];

    if (!firstCandidate) {
      throw new Error("No candidate available for explicit-confirm smoke test.");
    }

    await retainConfirmedMemory(firstCandidate);
    console.log("Confirmed one candidate after explicit opt-in.");
  } else {
    console.log(
      "No candidate was retained as canonical. Set CONFIRM_DEMO_MEMORY=1 to test explicit confirmation."
    );
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
