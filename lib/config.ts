import rubric from "../config/rubric_config.json";
import vector from "../config/vector_config.json";
import type { ModuleConfig, RubricConfig, VectorConfig } from "./types";

export function loadRubric(): RubricConfig {
  return rubric as RubricConfig;
}

export function loadVector(): VectorConfig {
  return vector as VectorConfig;
}

export function getModule(moduleId: number): ModuleConfig {
  const match = loadRubric().modules.find((module) => module.id === Number(moduleId));
  if (!match) {
    throw new Error(`Unknown module id: ${moduleId}. Valid ids are 1 through 9.`);
  }
  return match;
}

export function mappedVectorCodes(module: ModuleConfig): string[] {
  if (module.vector_blend === "all_six" || module.id === 9) {
    return ["V", "E", "C", "T", "O", "R"];
  }
  const codes: string[] = [];
  if (module.vector_primary) codes.push(module.vector_primary);
  if (module.vector_secondary && !codes.includes(module.vector_secondary)) {
    codes.push(module.vector_secondary);
  }
  return codes;
}
