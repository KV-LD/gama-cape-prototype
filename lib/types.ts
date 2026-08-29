export type ModuleConfig = {
  id: number;
  name: string;
  phase_ref?: string;
  exemptible?: boolean;
  vector_primary?: string;
  vector_secondary?: string;
  vector_blend?: string;
  vector_blend_weights?: Record<string, number>;
  skill_indices: { name: string; observable_behaviour: string }[];
};

export type RubricConfig = {
  blend: { module_weight: number; vector_weight: number };
  cutoffs: {
    completion_pass: number;
    exemption_pass: number;
    exemption_floor_per_dimension: number;
  };
  consistency_rule: { disagreement_threshold: number };
  modules: ModuleConfig[];
};

export type VectorConfig = {
  score_band_mapping: Record<string, number>;
  dimensions: Record<
    string,
    { name: string; definition: string; levels: Record<string, string> }
  >;
};

export type Submission = {
  written: string;
  code: string;
  text: string;
};

export type DefenseQA = { question: string; answer: string };

export type ScorePass = {
  pass_label: string;
  skill_scores: Record<string, number>;
  vector_scores: Record<string, number>;
  evidence: Record<string, string>;
  raw: unknown;
};

export type Reconciled = {
  final: number;
  borderline_review: boolean;
  disagreement: number;
  method: string;
};

export type ScoreSheet = {
  pass_a: ScorePass;
  pass_b: ScorePass;
  skill_final: Record<string, Reconciled>;
  vector_final: Record<string, Reconciled>;
  borderline_flags: unknown[];
  borderline_review: boolean;
  module_score: number;
  vector_score: number;
  final_blended_score: number;
  floor_violation: boolean;
  verdict: string;
  blend: RubricConfig["blend"];
  cutoffs: RubricConfig["cutoffs"];
};

export type AttemptRecord = {
  candidate_name: string;
  domain: string;
  module_id: number;
  module_name: string;
  tools: string[];
  hyperscaler: string | null;
  problem_statement: string;
  generation_prompt: string;
  generation_model?: string;
  submission: Submission;
  defense_qa: DefenseQA[];
  score_sheet: ScoreSheet;
  pass_a: ScorePass;
  pass_b: ScorePass;
  verdict: string;
  github_url?: string;
  html_report_url?: string;
  recorded_at?: string;
  mapped_vector_dimensions: string[];
};
