import React from 'react';
import { ChevronRight, FileText, Folder } from 'lucide-react';
import { LegalHierarchyNode } from '../../lib/types';

interface HierarchyTreeProps {
  nodes: LegalHierarchyNode[];
  selectedId?: string;
  onSelectNode: (node: LegalHierarchyNode) => void;
}

export const HierarchyTree: React.FC<HierarchyTreeProps> = ({
  nodes,
  selectedId,
  onSelectNode,
}) => {
  return (
    <div className="space-y-1 text-xs">
      {nodes.map((node) => {
        const isSelected = selectedId === node.id || selectedId === node.chunk_id;
        const hasChildren = node.children && node.children.length > 0;

        return (
          <div key={node.id} className="space-y-1">
            <button
              onClick={() => onSelectNode(node)}
              className={`w-full text-left px-2.5 py-1.5 rounded-md flex items-center justify-between transition ${
                isSelected
                  ? 'bg-blue-100/70 text-blue-900 font-semibold'
                  : 'text-slate-700 hover:bg-slate-100 hover:text-slate-900'
              }`}
            >
              <div className="flex items-center gap-2 truncate">
                {hasChildren ? (
                  <Folder className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
                ) : (
                  <FileText className="w-3.5 h-3.5 text-blue-600 flex-shrink-0" />
                )}
                <span className="truncate">{node.title}</span>
              </div>
              {node.page && (
                <span className="text-[10px] text-slate-400 font-mono flex-shrink-0">
                  p.{node.page}
                </span>
              )}
            </button>

            {hasChildren && (
              <div className="pl-4 border-l border-slate-200 ml-3 space-y-1">
                <HierarchyTree
                  nodes={node.children}
                  selectedId={selectedId}
                  onSelectNode={onSelectNode}
                />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};
