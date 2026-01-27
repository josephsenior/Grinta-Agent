/**
 * Sound Effects System for UI interactions
 * Subtle, non-intrusive audio feedback
 */

class SoundEffects {
  private audioContext: AudioContext | null = null;

  private enabled: boolean = true;

  private volume: number = 0.15; // Very subtle

  constructor() {
    if (typeof window !== "undefined") {
      // Check user preference
      const savedPreference = localStorage.getItem("sound-effects-enabled");
      this.enabled = savedPreference !== "false";
    }
  }

  private getContext(): AudioContext {
    if (!this.audioContext && typeof window !== "undefined") {
      // Handle webkit-prefixed AudioContext for older browsers
      const AudioContextClass =
        window.AudioContext ||
        (window as unknown as { webkitAudioContext: typeof AudioContext })
          .webkitAudioContext;
      this.audioContext = new AudioContextClass();
    }
    return this.audioContext!;
  }

  /**
   * Play a subtle hover sound
   */
  hover() {
    if (!this.enabled) return;

    try {
      const ctx = this.getContext();
      const oscillator = ctx.createOscillator();
      const gainNode = ctx.createGain();

      oscillator.connect(gainNode);
      gainNode.connect(ctx.destination);

      // Subtle high-pitched click
      oscillator.frequency.setValueAtTime(800, ctx.currentTime);
      oscillator.type = "sine";

      gainNode.gain.setValueAtTime(0, ctx.currentTime);
      gainNode.gain.linearRampToValueAtTime(
        this.volume * 0.3,
        ctx.currentTime + 0.01,
      );
      gainNode.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.08);

      oscillator.start(ctx.currentTime);
      oscillator.stop(ctx.currentTime + 0.08);
    } catch (e) {
      // Silently fail if audio context issues
    }
  }

  /**
   * Play success sound (button click, action complete)
   */
  success() {
    if (!this.enabled) return;

    try {
      const ctx = this.getContext();

      // Two-note ascending chime
      const playNote = (frequency: number, delay: number) => {
        const oscillator = ctx.createOscillator();
        const gainNode = ctx.createGain();

        oscillator.connect(gainNode);
        gainNode.connect(ctx.destination);

        oscillator.frequency.setValueAtTime(frequency, ctx.currentTime + delay);
        oscillator.type = "sine";

        gainNode.gain.setValueAtTime(0, ctx.currentTime + delay);
        gainNode.gain.linearRampToValueAtTime(
          this.volume * 0.5,
          ctx.currentTime + delay + 0.01,
        );
        gainNode.gain.exponentialRampToValueAtTime(
          0.01,
          ctx.currentTime + delay + 0.15,
        );

        oscillator.start(ctx.currentTime + delay);
        oscillator.stop(ctx.currentTime + delay + 0.15);
      };

      playNote(600, 0);
      playNote(800, 0.05);
    } catch (e) {
      // Silently fail
    }
  }

  /**
   * Play click sound
   */
  click() {
    if (!this.enabled) return;

    try {
      const ctx = this.getContext();
      const oscillator = ctx.createOscillator();
      const gainNode = ctx.createGain();

      oscillator.connect(gainNode);
      gainNode.connect(ctx.destination);

      oscillator.frequency.setValueAtTime(400, ctx.currentTime);
      oscillator.type = "square";

      gainNode.gain.setValueAtTime(0, ctx.currentTime);
      gainNode.gain.linearRampToValueAtTime(
        this.volume * 0.4,
        ctx.currentTime + 0.005,
      );
      gainNode.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.05);

      oscillator.start(ctx.currentTime);
      oscillator.stop(ctx.currentTime + 0.05);
    } catch (e) {
      // Silently fail
    }
  }

  /**
   * Play error sound
   */
  error() {
    if (!this.enabled) return;

    try {
      const ctx = this.getContext();
      const oscillator = ctx.createOscillator();
      const gainNode = ctx.createGain();

      oscillator.connect(gainNode);
      gainNode.connect(ctx.destination);

      // Descending tone
      oscillator.frequency.setValueAtTime(600, ctx.currentTime);
      oscillator.frequency.exponentialRampToValueAtTime(
        300,
        ctx.currentTime + 0.1,
      );
      oscillator.type = "sawtooth";

      gainNode.gain.setValueAtTime(0, ctx.currentTime);
      gainNode.gain.linearRampToValueAtTime(
        this.volume * 0.3,
        ctx.currentTime + 0.01,
      );
      gainNode.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.12);

      oscillator.start(ctx.currentTime);
      oscillator.stop(ctx.currentTime + 0.12);
    } catch (e) {
      // Silently fail
    }
  }

  /**
   * Toggle sound effects
   */
  toggle() {
    this.enabled = !this.enabled;
    if (typeof window !== "undefined") {
      localStorage.setItem("sound-effects-enabled", String(this.enabled));
    }
    return this.enabled;
  }

  /**
   * Set volume (0-1)
   */
  setVolume(vol: number) {
    this.volume = Math.max(0, Math.min(1, vol));
  }

  /**
   * Check if enabled
   */
  isEnabled() {
    return this.enabled;
  }
}

// Singleton instance
export const soundEffects = new SoundEffects();
