import { SuggestedTask } from "#/components/features/home/tasks/task.types";
import { Forge } from "../forge-axios";

export class SuggestionsService {
  static async getSuggestedTasks(): Promise<SuggestedTask[]> {
    const { data } = await Forge.get("/api/user/suggested-tasks");
    return data;
  }
}
