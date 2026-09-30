import { useCallback, useEffect, useRef } from 'react';
import type { CSSProperties, MouseEvent as ReactMouseEvent, ReactNode } from 'react';

/**
 * Shared modal primitive.
 *
 * Every overlay in this app needs the same six things, and hand-rolling them per
 * component is how they get forgotten:
 *   1. `role="dialog"` + `aria-modal="true"` so assistive tech treats the
 *      content as a modal and hides the rest of the page.
 *   2. `aria-labelledby` pointing at a real heading, so the dialog is announced
 *      by name rather than as an unlabelled "dialog".
 *   3. Focus moved INTO the panel on open.
 *   4. A focus trap: Tab / Shift+Tab cycle within the panel instead of escaping
 *      to the page behind the backdrop.
 *   5. Escape to dismiss.
 *   6. Focus restored to whatever was focused before the dialog opened.
 *
 * Plus backdrop click-to-close, which only fires for clicks that land on the
 * backdrop itself (not clicks that bubble up from inside the panel).
 */

/** Everything that can receive keyboard focus, minus disabled elements. */
const FOCUSABLE_SELECTOR = [
  'a[href]',
  'area[href]',
  'button:not([disabled])',
  'input:not([disabled]):not([type="hidden"])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  'iframe',
  'object',
  'embed',
  'summary',
  '[contenteditable="true"]',
  '[tabindex]:not([tabindex="-1"])'
].join(',');

function isVisible(element: HTMLElement): boolean {
  // getClientRects() is empty for `display: none` subtrees. Keep the currently
  // focused element eligible even if it is mid-transition.
  return element.getClientRects().length > 0 || element === document.activeElement;
}

function getFocusable(container: HTMLElement): HTMLElement[] {
  return Array.from(container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)).filter(
    (el) => !el.hasAttribute('disabled') && el.getAttribute('aria-hidden') !== 'true' && isVisible(el)
  );
}

export interface DialogProps {
  /** When false the dialog renders nothing at all. */
  open: boolean;
  /** Called for Escape, backdrop click, and unmount-equivalent dismissal. */
  onClose: () => void;
  /**
   * `id` of the element that names this dialog. Must exist in the rendered tree.
   * Either pass `title` (Dialog renders the heading) or render your own element
   * carrying this id inside `children`.
   */
  labelledBy: string;
  /**
   * Optional heading text. When provided, Dialog renders it as an `<h2>` with
   * `id={labelledBy}`. Omit it when the dialog needs a custom header layout
   * (icon + badge, etc.) and put the id on your own heading instead.
   */
  title?: ReactNode;
  children: ReactNode;
  /** Style overrides for the heading rendered from `title`. */
  titleStyle?: CSSProperties;
  describedBy?: string;
  panelClassName?: string;
  panelStyle?: CSSProperties;
  backdropClassName?: string;
  backdropStyle?: CSSProperties;
}

export function Dialog({
  open,
  onClose,
  labelledBy,
  title,
  children,
  titleStyle,
  describedBy,
  panelClassName,
  panelStyle,
  backdropClassName,
  backdropStyle
}: DialogProps) {
  const backdropRef = useRef<HTMLDivElement | null>(null);
  const panelRef = useRef<HTMLDivElement | null>(null);

  // Move focus into the dialog on open; restore it to the trigger on close.
  useEffect(() => {
    if (!open) return;
    const previouslyFocused =
      document.activeElement instanceof HTMLElement ? document.activeElement : null;

    const panel = panelRef.current;
    if (panel) {
      const focusables = getFocusable(panel);
      (focusables[0] ?? panel).focus();
    }

    return () => {
      // `previouslyFocused` may have been unmounted by the close handler; guard.
      if (previouslyFocused && previouslyFocused.isConnected) {
        previouslyFocused.focus();
      }
    };
  }, [open]);

  // Escape + Tab trap, bound at the document so focus cannot be stranded
  // outside the panel by a stray click.
  useEffect(() => {
    if (!open) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        event.stopPropagation();
        onClose();
        return;
      }
      if (event.key !== 'Tab') return;

      const panel = panelRef.current;
      if (!panel) return;

      const focusables = getFocusable(panel);
      if (focusables.length === 0) {
        event.preventDefault();
        panel.focus();
        return;
      }

      const first = focusables[0];
      const last = focusables[focusables.length - 1];
      const active = document.activeElement;
      const focusIsInside = active instanceof Node && panel.contains(active);

      if (!focusIsInside) {
        event.preventDefault();
        (event.shiftKey ? last : first).focus();
      } else if (event.shiftKey && active === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && active === last) {
        event.preventDefault();
        first.focus();
      }
    };

    document.addEventListener('keydown', handleKeyDown, true);
    return () => document.removeEventListener('keydown', handleKeyDown, true);
  }, [open, onClose]);

  const handleBackdropClick = useCallback(
    (event: ReactMouseEvent<HTMLDivElement>) => {
      // Only dismiss when the click target is the backdrop itself. Clicks that
      // bubble out of the panel must not close the dialog.
      if (event.target === backdropRef.current) onClose();
    },
    [onClose]
  );

  if (!open) return null;

  return (
    <div
      ref={backdropRef}
      className={backdropClassName ?? 'overlay-backdrop'}
      style={backdropStyle}
      onClick={handleBackdropClick}
    >
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={labelledBy}
        aria-describedby={describedBy}
        tabIndex={-1}
        className={panelClassName}
        style={{ outline: 'none', ...panelStyle }}
      >
        {title !== undefined && (
          <h2
            id={labelledBy}
            style={{ margin: 0, fontSize: '1.15rem', fontWeight: 700, color: '#111827', ...titleStyle }}
          >
            {title}
          </h2>
        )}
        {children}
      </div>
    </div>
  );
}
