"use client";

import {
  CheckCircle,
  Flask,
  LockKey,
  Play,
  ShieldWarning,
  Target,
  WarningCircle,
  XCircle,
} from "@phosphor-icons/react";
import { useMemo, useState } from "react";

import type {
  AdminEvaluation,
  EvaluationRiskCoverage,
} from "@/lib/types";

type OutcomeFilter = "all" | "passed" | "failed" | "not_run";

type EvaluationDashboardProps = {
  report: AdminEvaluation;
  onRun: () => void;
};

function formatTimestamp(value: string | undefined) {
  if (!value) return "Chưa có";
  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "short",
    timeStyle: "short",
    timeZone: "Asia/Ho_Chi_Minh",
  }).format(new Date(value));
}

function displayText(value: string) {
  return value.replace(/[—–]/g, "-");
}

function riskLabel(
  riskId: EvaluationRiskCoverage["id"],
  report: AdminEvaluation,
) {
  return report.risk_coverage.find((risk) => risk.id === riskId)?.label ?? riskId;
}

export function EvaluationDashboard({
  report,
  onRun,
}: EvaluationDashboardProps) {
  const [outcomeFilter, setOutcomeFilter] = useState<OutcomeFilter>("all");
  const [riskFilter, setRiskFilter] = useState("");
  const baseline = report.baseline_run;
  const latest = report.latest_run;
  const isRunning = ["starting", "running"].includes(report.run_status.state);
  const resultById = useMemo(
    () =>
      new Map(
        (latest?.results ?? []).map((result) => [result.case_id, result] as const),
      ),
    [latest],
  );
  const visibleCases = useMemo(
    () =>
      report.cases.filter((testCase) => {
        const result = resultById.get(testCase.id);
        const matchesRisk =
          !riskFilter ||
          testCase.risk_types.includes(
            riskFilter as EvaluationRiskCoverage["id"],
          );
        const matchesOutcome =
          outcomeFilter === "all" ||
          (outcomeFilter === "passed" && result?.passed) ||
          (outcomeFilter === "failed" && result && !result.passed) ||
          (outcomeFilter === "not_run" && !result);
        return matchesRisk && matchesOutcome;
      }),
    [outcomeFilter, report.cases, resultById, riskFilter],
  );

  return (
    <div className="eval-dashboard">
      <section className="eval-decision" aria-labelledby="eval-decision-title">
        <div className="eval-decision-icon">
          <Target size={22} weight="fill" />
        </div>
        <div>
          <p>AI decision contract</p>
          <h2 id="eval-decision-title">{report.decision_statement}</h2>
          <span>{report.decision_problem}</span>
        </div>
        <dl>
          <div>
            <dt>Provider</dt>
            <dd>{report.provider}</dd>
          </div>
          <div>
            <dt>Model</dt>
            <dd>{report.model}</dd>
          </div>
        </dl>
      </section>

      <section className="eval-metrics" aria-label="Số liệu bộ thử">
        <article>
          <p>Tổng câu thử</p>
          <strong>{report.total_cases}</strong>
          <span>Tối thiểu yêu cầu: 20</span>
        </article>
        <article>
          <p>Kiểu tình huống</p>
          <strong>{report.risk_coverage.filter((risk) => risk.met).length}/4</strong>
          <span>Mỗi kiểu có ít nhất 2 câu</span>
        </article>
        <article>
          <p>Từ quan sát thật</p>
          <strong>{report.observed_cases}</strong>
          <span>Khuyến nghị: từ 10 câu</span>
        </article>
        <article>
          <p>Lần chạy đầu</p>
          <strong>
            {baseline
              ? `${baseline.summary.passed}/${baseline.summary.total}`
              : "Chưa chạy"}
          </strong>
          <span>
            {baseline
              ? `${baseline.summary.pass_rate}% đạt`
              : "Chưa có baseline result"}
          </span>
        </article>
      </section>

      <div className="eval-contract-grid">
        <section className="eval-threshold">
          <div className="eval-section-heading">
            <div>
              <h2>Chuẩn đạt đã khóa</h2>
              <p>Cam kết giữ nguyên sau khi nhìn thấy kết quả.</p>
            </div>
            <span className="eval-lock">
              <LockKey size={13} weight="fill" />
              Đã khóa
            </span>
          </div>
          <div className="eval-threshold-value">
            <strong>≥{report.acceptance_threshold.overall_percent}%</strong>
            <span>tổng số câu phải đạt</span>
          </div>
          <div className="eval-zero-rule">
            <ShieldWarning size={19} weight="fill" />
            <div>
              <p>Không cho phép sai</p>
              <strong>{report.acceptance_threshold.zero_tolerance_rule}</strong>
            </div>
          </div>
          {baseline && (
            <div
              className={
                baseline.summary.accepted
                  ? "eval-baseline-status eval-status-pass"
                  : "eval-baseline-status eval-status-fail"
              }
            >
              {baseline.summary.accepted ? (
                <CheckCircle size={17} weight="fill" />
              ) : (
                <WarningCircle size={17} weight="fill" />
              )}
              <span>
                {baseline.summary.accepted
                  ? "Baseline đạt chuẩn đã cam kết."
                  : "Baseline chưa đạt. Giữ nguyên chuẩn và phân tích khoảng cách."}
              </span>
            </div>
          )}
        </section>

        <section className="eval-coverage">
          <div className="eval-section-heading">
            <div>
              <h2>Độ phủ tình huống</h2>
              <p>Đủ cả bốn failure path bắt buộc.</p>
            </div>
          </div>
          <div className="eval-risk-grid">
            {report.risk_coverage.map((risk) => (
              <article key={risk.id}>
                <div>
                  {risk.met ? (
                    <CheckCircle size={17} weight="fill" />
                  ) : (
                    <WarningCircle size={17} weight="fill" />
                  )}
                  <strong>{risk.label}</strong>
                </div>
                <p>{risk.description}</p>
                <span>
                  {risk.count} câu, yêu cầu tối thiểu {risk.minimum}
                </span>
              </article>
            ))}
          </div>
        </section>
      </div>

      <section className="eval-results">
        <div className="eval-results-head">
          <div>
            <h2>Kết quả đầy đủ</h2>
            <p>
              {latest
                ? `${latest.summary.passed}/${latest.summary.total} câu đạt trong lần chạy ${formatTimestamp(latest.completed_at)}.`
                : "Chưa có lần chạy nào. Bộ câu vẫn có thể được kiểm tra trước khi chạy."}
            </p>
          </div>
          <button
            className="button"
            type="button"
            onClick={onRun}
            disabled={isRunning}
          >
            <Play size={14} weight="fill" />
            {isRunning ? "Đang chạy" : "Chạy lại 24 câu"}
          </button>
        </div>

        {isRunning && (
          <div className="eval-running" role="status">
            <Flask size={17} />
            <span>
              Đã chạy {report.run_status.completed_cases}/
              {report.run_status.total_cases} câu. Có thể rời tab và quay lại sau.
            </span>
          </div>
        )}

        <div className="eval-filters">
          <div aria-label="Lọc theo kết quả">
            {(
              [
                ["all", "Tất cả"],
                ["passed", "Đạt"],
                ["failed", "Chưa đạt"],
                ["not_run", "Chưa chạy"],
              ] as const
            ).map(([value, label]) => (
              <button
                className={outcomeFilter === value ? "eval-filter-active" : ""}
                type="button"
                key={value}
                onClick={() => setOutcomeFilter(value)}
              >
                {label}
              </button>
            ))}
          </div>
          <label>
            <span className="sr-only">Lọc theo kiểu tình huống</span>
            <select
              value={riskFilter}
              onChange={(event) => setRiskFilter(event.target.value)}
            >
              <option value="">Tất cả tình huống</option>
              {report.risk_coverage.map((risk) => (
                <option value={risk.id} key={risk.id}>
                  {risk.label}
                </option>
              ))}
            </select>
          </label>
          <span>{visibleCases.length} câu đang hiển thị</span>
        </div>

        <div className="eval-case-list">
          {visibleCases.map((testCase) => {
            const result = resultById.get(testCase.id);
            return (
              <details className="eval-case" key={testCase.id}>
                <summary>
                  <div className="eval-case-id">
                    <code>{testCase.id}</code>
                    {testCase.origin.observed && <span>Quan sát thật</span>}
                    {testCase.critical && <span className="eval-critical">Deadline</span>}
                  </div>
                  <div className="eval-case-title">
                    <strong>{testCase.title}</strong>
                    <p>{testCase.input.message}</p>
                  </div>
                  <div className="eval-case-risks">
                    {testCase.risk_types.map((risk) => (
                      <span key={risk}>{riskLabel(risk, report)}</span>
                    ))}
                  </div>
                  <div
                    className={
                      result
                        ? result.passed
                          ? "eval-result-state eval-state-pass"
                          : "eval-result-state eval-state-fail"
                        : "eval-result-state"
                    }
                  >
                    {result ? (
                      result.passed ? (
                        <CheckCircle size={16} weight="fill" />
                      ) : (
                        <XCircle size={16} weight="fill" />
                      )
                    ) : (
                      <Flask size={16} />
                    )}
                    {result ? (result.passed ? "Đạt" : "Chưa đạt") : "Chưa chạy"}
                  </div>
                </summary>
                <div className="eval-case-detail">
                  <div>
                    <h3>Phải trả lời</h3>
                    <p>{testCase.expected_behavior}</p>
                  </div>
                  <div>
                    <h3>Sản phẩm đã trả lời</h3>
                    <p>
                      {result?.answer
                        ? displayText(result.answer)
                        : "Case chưa được chạy qua sản phẩm trong lần hiện tại."}
                    </p>
                  </div>
                  <div>
                    <h3>Validator</h3>
                    {result ? (
                      <ul>
                        {result.checks.map((check) => (
                          <li key={`${testCase.id}-${check.name}`}>
                            {check.passed ? (
                              <CheckCircle size={14} weight="fill" />
                            ) : (
                              <XCircle size={14} weight="fill" />
                            )}
                            <span>{check.detail}</span>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <pre>{JSON.stringify(testCase.checks, null, 2)}</pre>
                    )}
                  </div>
                  <dl>
                    <div>
                      <dt>Nguồn tình huống</dt>
                      <dd>{testCase.origin.reference}</dd>
                    </div>
                    <div>
                      <dt>Citation</dt>
                      <dd>{result?.citations.length ?? 0}</dd>
                    </div>
                    <div>
                      <dt>Latency</dt>
                      <dd>
                        {result
                          ? `${(result.latency_ms / 1000).toFixed(1)} giây`
                          : "Chưa có"}
                      </dd>
                    </div>
                    <div>
                      <dt>Provider</dt>
                      <dd>{result?.provider ?? "Chưa có"}</dd>
                    </div>
                  </dl>
                </div>
              </details>
            );
          })}
        </div>

        {visibleCases.length === 0 && (
          <div className="admin-empty">
            <Flask size={24} />
            <h3>Không có câu phù hợp bộ lọc</h3>
            <p>Đổi kết quả hoặc kiểu tình huống để xem các case khác.</p>
          </div>
        )}
      </section>
    </div>
  );
}
