type LookupMasterData = {
  departments?: { id: string; code?: string; name: string }[];
  labs?: { id: string; code?: string; name: string }[];
  experiments?: { id: string; name: string; labId: string }[];
};

type UserNameLookup = Record<string, string | undefined>;

export function displayUserName(
  userId: string | null | undefined,
  usersById: UserNameLookup,
  currentUser?: { id: string; name: string } | null
) {
  if (!userId) return "-";
  if (currentUser?.id === userId) return currentUser.name || "目前使用者";
  return usersById[userId] || "未知使用者";
}

export function displayDepartmentName(
  masterData: LookupMasterData,
  departmentId: string | null | undefined
) {
  if (!departmentId) return "-";
  return (
    masterData.departments?.find(
      (department) => department.id === departmentId || department.code === departmentId
    )?.name || "未知部門"
  );
}

export function displayLabName(masterData: LookupMasterData, labId: string | null | undefined) {
  if (!labId) return "-";
  return (
    masterData.labs?.find((lab) => lab.id === labId || lab.code === labId)?.name || "未知實驗室"
  );
}

export function displayExperimentName(
  masterData: LookupMasterData,
  experimentId: string | null | undefined
) {
  if (!experimentId) return "-";
  return (
    masterData.experiments?.find((experiment) => experiment.id === experimentId)?.name || "未知實驗"
  );
}

export function displayScopeName(
  masterData: LookupMasterData,
  usersById: UserNameLookup,
  scopeType: string,
  scopeId: string,
  currentUser?: { id: string; name: string } | null
) {
  if (scopeType === "user") return displayUserName(scopeId, usersById, currentUser);
  if (scopeType === "department") return displayDepartmentName(masterData, scopeId);
  if (scopeType === "lab") return displayLabName(masterData, scopeId);
  return scopeId || "-";
}
