import { useCallback, useEffect, useRef, useState } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { emptyMasterData } from "../constants";
import { requestJson } from "../lib/api";
import {
  createDefaultItem,
  getNextSampleId,
  groupItemsBySample,
  toggleExperimentInGroup,
} from "../lib/formItems";
import { readTemplates, writeTemplates } from "../lib/templates";
import type {
  Experiment,
  FormItem,
  OrderTemplate,
  SampleFormGroup,
  TemplateMasterData,
} from "../types";

export function useOrderTemplatesPage() {
  const { user } = useAuth();
  const currentUserId = user?.id ?? "";
  const currentUserName = user?.name ?? currentUserId;
  const applicantId = currentUserId;

  const [templates, setTemplates] = useState<OrderTemplate[]>([]);
  const [masterData, setMasterData] = useState<TemplateMasterData>({
    labs: emptyMasterData.labs,
    experiments: emptyMasterData.experiments,
  });
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null);
  const [templateName, setTemplateName] = useState("");
  const [items, setItems] = useState<FormItem[]>([{ ...createDefaultItem(emptyMasterData) }]);
  const [message, setMessage] = useState("選擇既有模板，或建立一個新的樣品實驗模板。");
  const [nameError, setNameError] = useState("");
  const nameInputRef = useRef<HTMLInputElement | null>(null);

  const loadTemplates = useCallback((userId: string) => {
    setTemplates(readTemplates(userId));
  }, []);

  const persistTemplates = useCallback(
    (nextTemplates: OrderTemplate[]) => {
      setTemplates(nextTemplates);
      writeTemplates(applicantId, nextTemplates);
    },
    [applicantId]
  );

  const resetEditor = useCallback(() => {
    setSelectedTemplateId(null);
    setTemplateName("");
    setItems([{ ...createDefaultItem(masterData) }]);
    setMessage("已清空編輯區，可以建立新模板。");
  }, [masterData]);

  function selectTemplate(template: OrderTemplate) {
    setSelectedTemplateId(template.id);
    setTemplateName(template.name);
    setItems(template.items.map((item) => ({ ...item })));
    setMessage(`正在編輯模板：${template.name}`);
  }

  function saveTemplate() {
    const name = templateName.trim();

    if (!name) {
      setNameError("模板名稱不可為空");
      setMessage("請先輸入模板名稱。");
      nameInputRef.current?.focus();
      return;
    }

    if (
      items.some((item) => !item.sampleId.trim() || !item.labId.trim() || !item.experimentId.trim())
    ) {
      setMessage("每個樣品與實驗都需要填寫樣品編號、實驗室與實驗項目。");
      return;
    }

    const now = new Date().toISOString();

    if (selectedTemplateId) {
      const nextTemplates = templates.map((template) =>
        template.id === selectedTemplateId
          ? { ...template, name, items: items.map((item) => ({ ...item })), updatedAt: now }
          : template
      );
      persistTemplates(nextTemplates);
      setMessage(`已更新模板：${name}`);
      return;
    }

    const nextTemplate: OrderTemplate = {
      id: `${Date.now()}`,
      name,
      items: items.map((item) => ({ ...item })),
      createdAt: now,
      updatedAt: now,
    };

    persistTemplates([nextTemplate, ...templates]);
    setSelectedTemplateId(nextTemplate.id);
    setMessage(`已建立模板：${name}`);
  }

  function deleteTemplate(templateId: string) {
    const template = templates.find((item) => item.id === templateId);
    const nextTemplates = templates.filter((item) => item.id !== templateId);

    persistTemplates(nextTemplates);

    if (selectedTemplateId === templateId) {
      resetEditor();
    }

    setMessage(`已刪除模板：${template?.name || templateId}`);
  }

  function addSample() {
    setItems((current) => [...current, createDefaultItem(masterData, getNextSampleId(current))]);
  }

  function removeItem(index: number) {
    setItems((current) =>
      current.length <= 1 ? current : current.filter((_, itemIndex) => itemIndex !== index)
    );
  }

  function updateSampleGroup(group: SampleFormGroup, sampleId: string) {
    setItems((current) =>
      current.map((item, index) =>
        index >= group.startIndex && index <= group.endIndex ? { ...item, sampleId } : item
      )
    );
  }

  function updateSampleNameGroup(group: SampleFormGroup, sampleName: string) {
    setItems((current) =>
      current.map((item, index) =>
        index >= group.startIndex && index <= group.endIndex ? { ...item, sampleName } : item
      )
    );
  }

  function updateDependencyField(
    index: number,
    field: "targetGroup" | "target",
    value: string | number
  ) {
    setItems((current) =>
      current.map((item, itemIndex) => {
        if (itemIndex !== index) return item;

        if (field === "target") {
          return {
            ...item,
            target: Math.max(1, Number(value) || 1),
          };
        }

        return {
          ...item,
          targetGroup: String(value).trim() || "G1",
        };
      })
    );
  }

  function moveExperiment(index: number, direction: -1 | 1) {
    setItems((current) => {
      const targetIndex = index + direction;
      const item = current[index];
      const target = current[targetIndex];

      if (!item || !target || item.sampleId !== target.sampleId) {
        return current;
      }

      const next = [...current];
      [next[index], next[targetIndex]] = [next[targetIndex], next[index]];
      return next;
    });
  }

  function toggleExperimentForSample(
    group: SampleFormGroup,
    experiment: Experiment,
    checked: boolean
  ) {
    setItems((current) => toggleExperimentInGroup(current, group, experiment, checked));
  }

  useEffect(() => {
    async function loadMasterData() {
      try {
        const response = await requestJson<TemplateMasterData>("/api/master-data");
        const nextMasterData = {
          labs: response.data.labs,
          experiments: response.data.experiments,
        };

        setMasterData(nextMasterData);
        setItems([{ ...createDefaultItem(nextMasterData) }]);
      } catch {
        setMasterData({
          labs: emptyMasterData.labs,
          experiments: emptyMasterData.experiments,
        });
      }
    }

    void loadMasterData();
  }, []);

  useEffect(() => {
    if (!applicantId) {
      return;
    }

    queueMicrotask(() => {
      loadTemplates(applicantId);
      resetEditor();
    });
  }, [applicantId, loadTemplates, resetEditor]);

  return {
    applicantId,
    currentUserName,
    templates,
    masterData,
    selectedTemplateId,
    templateName,
    setTemplateName,
    items,
    message,
    nameError,
    setNameError,
    nameInputRef,
    sampleGroups: groupItemsBySample(items),
    resetEditor,
    selectTemplate,
    saveTemplate,
    deleteTemplate,
    addSample,
    removeItem,
    updateSampleGroup,
    updateSampleNameGroup,
    updateDependencyField,
    moveExperiment,
    toggleExperimentForSample,
  };
}
