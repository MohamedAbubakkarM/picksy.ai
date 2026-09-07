import { inter, sora, poppins, epilogue } from "@/app/ui/fonts";
import { AiOutlineDingding } from "react-icons/ai";



const Sidebar = () => {
    return (
        <div className="h-screen w-60 bg-[#1E1E1E] text-white flex flex-col justify-between p-4 border-t">
            {/* Website Name */}
            <div>
                <AiOutlineDingding size={60} className="ml-13 mb-8 mt-2" color="#FFC30B"/>

                {/* Menu Items */}
                <ul className="space-y-4">
                    <li className={`cursor-pointer ${epilogue.className} pl-4 text-[#B0B0B0] hover:bg-[#FFC30B] hover:text-[white] p-2 rounded`}>New chat</li>
                    <li className={`cursor-pointer ${epilogue.className} pl-4 text-[#B0B0B0] hover:bg-[#FFC30B] hover:text-[white] p-2 rounded`}>History</li>
                </ul>
            </div>

            {/* User Profile */}
            <div className="border-t border-gray-700 pt-4">
            <div className="flex items-center space-x-3">
          <div>
            <p className={`text-sm ${epilogue.className} font-medium text-[#E0E0E0]`}>Md</p>
            <p className={`text-xs text-gray-400 ${epilogue.className}`}>View Profile</p>
          </div>
        </div>

            </div>
        </div>



    )
}

export default Sidebar;