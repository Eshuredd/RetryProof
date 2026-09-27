interface WorkflowStepProps {
  index: number;
  title: string;
  description: string;
}

export function WorkflowStep({ index, title, description }: WorkflowStepProps) {
  return (
    <div className="flex gap-4 py-4 border-b border-[#e5e7eb] last:border-b-0">
      <div className="flex-shrink-0 w-7 h-7 rounded-full bg-[#3b82d4] text-white text-xs font-bold flex items-center justify-center mt-0.5">
        {index}
      </div>
      <div>
        <p className="font-semibold text-sm text-[#1f2328]">{title}</p>
        <p className="text-sm text-[#57606a] mt-0.5">{description}</p>
      </div>
    </div>
  );
}
