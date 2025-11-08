import { Forge } from "./forge-axios";
import {
  CustomSecret,
  GetSecretsResponse,
  POSTProviderTokens,
} from "./secrets-service.types";
import { Provider, ProviderToken } from "#/types/settings";

export class SecretsService {
  static async getSecrets() {
    const { data } = await Forge.get<GetSecretsResponse>("/api/secrets");
    return data.custom_secrets;
  }

  static async createSecret(name: string, value: string, description?: string) {
    const secret: CustomSecret = {
      name,
      value,
      description,
    };

    const { status } = await Forge.post("/api/secrets", secret);
    return status === 201;
  }

  static async updateSecret(id: string, name: string, description?: string) {
    const secret: Omit<CustomSecret, "value"> = {
      name,
      description,
    };

    const { status } = await Forge.put(`/api/secrets/${id}`, secret);
    return status === 200;
  }

  static async deleteSecret(id: string) {
    const { status } = await Forge.delete<boolean>(`/api/secrets/${id}`);
    return status === 200;
  }

  static async addGitProvider(providers: Record<Provider, ProviderToken>) {
    const tokens: POSTProviderTokens = {
      provider_tokens: providers,
    };
    const { data } = await Forge.post<boolean>(
      "/api/add-git-providers",
      tokens,
    );
    return data;
  }
}
