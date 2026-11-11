import type { ReactNode } from 'react';

interface Props {
  kicker: string;
  title: string;
  description?: string;
  actions?: ReactNode;
}

export const SectionHead = ({ kicker, title, description, actions }: Props) => (
  <div className="section-head">
    <div>
      <div className="kicker">{kicker}</div>
      <h2 className="section-title">{title}</h2>
      {description ? <p className="section-desc">{description}</p> : null}
    </div>
    {actions ? <div className="section-actions">{actions}</div> : null}
  </div>
);
